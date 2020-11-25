import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import ckan.lib.uploader as upl
import ckan.model as model
import ckan.logic as logic
from ckan.lib.base import abort
from ckan.logic.converters import convert_package_name_or_id_to_id
from ckan.common import g
import json
from copy import deepcopy
from flask import Blueprint
from os import path
from cdsaccess_plugin import SpecialAccessRights
from resource_category import ResourceCategory
from plugin import License, Publication, DataFormat, Person
from landing_page_plugin import landing_page_location

import pdb


def users_with_access(pkg_id):
    return [usr.id for usr in model.Session.query(SpecialAccessRights).
            filter(SpecialAccessRights.package_id == pkg_id).all()]


def extract_sigma2_metadata(pkg_info):

    datasets, person_ids, org_ids, license_ids, pub_ids =\
        sigma2_dataset_metadata(pkg_info)

    return {'datasets': datasets,
            'persons': sigma2_person_metadata(person_ids),
            'publications' : sigma2_publication_metadata(pub_ids),
            'organizations': sigma2_organization_metadata(org_ids),
            'licenses': sigma2_license_metadata(license_ids)}


def sigma2_dataset_metadata(pkg_info):

    parent_dataset, person_ids, org_ids, license_ids, pub_ids =\
        sigma2_parent_dataset_metadata(pkg_info)

    component_datasets = sigma2_dataset_component_metadata(pkg_info,
                                                           parent_dataset)

    datasets = [parent_dataset] + component_datasets
    return datasets, person_ids, org_ids, license_ids, pub_ids


def _remove_duplicate(lst):
    return list(dict.fromkeys(lst))


def sigma2_parent_dataset_metadata(pkg_info):

    context = {'model': model, 'session': model.Session,
               'user': g.user, 'for_view': True,
               'auth_user_obj': g.userobj}
    
    person_ids, org_ids, license_ids, pub_ids = [], [], [], []

    # constant metadata (always the same for export to Sigma2)
    language = 'English'  # always English
    category = 'Observation'  # we use 'Observation' as default.
    journal = ''
    bibliographic_citation = '' # how should this dataset be cited
    subject = 'geological CO2 storage'  # always, for now
    project = 'CO2DataShare'

    # trivial metadata (single fields that can be read right out of pkg_info)
    description = pkg_info['notes']
    title = pkg_info['title']
    identifier = pkg_info['doi']
    created_on = pkg_info['metadata_created']
    location = pkg_info['location']

    # set rights holder
    rights_holder = []
    if pkg_info.get('organization'):
        rights_holder = {'name': pkg_info.get('organization')['title'],
                         'id': pkg_info.get('organization')['id']}
        org_ids.append(pkg_info.get('organization')['id'])

    # set status and access rights
    status = 'embargoed' if pkg_info.get('access_level') == 'Embargoed' \
        else 'published'
    access_rights = 'public'
    if pkg_info.get('access_level') == 'Open':
        access_rights = users_with_access(pkg_info['id'])
        person_ids.extend(access_rights)

    # set contributor(s)
    contributor = [
        {'id': x[0], 'name': x[1]} for x in
        pkg_info['person_contributor'] + pkg_info['org_contributor']]
    person_ids.extend([x[0] for x in pkg_info['person_contributor']])
    org_ids.extend([x[0] for x in pkg_info['org_contributor']])
    creator = contributor  # we cannot make any distinguishment here

    data_manager = [x[0] for x in pkg_info['contact_person']]
    person_ids.extend(data_manager)

    # set license
    license = pkg_info['cdslicense']
    license_ids.append(license)

    # set rights (url to license)
    rights = ''
    if license:
        lobj = model.Session.query(License).get(pkg_info['cdslicense'])
        if lobj:
            rights = lobj.license_url

    # citations
    citations = [{'id': x[0], 'title': x[1]} for x in pkg_info['publications']]
    pub_ids.extend([x[0] for x in pkg_info['publications']])

    # temporal coverage
    temporal_coverage = [pkg_info['temporal_coverage_start'],
                         pkg_info['temporal_coverage_end']]

    # information fields to add to 'description'
    if len(description) > 0:
        # separate new content from existing by adding a couple of lines
        description += '\n\n\n'

    description += 'Project type: ' + pkg_info['project_type'] + '\n\n'

    if pkg_info['related_dataset']:
        description += 'Related dataset(s):\n'
        for rd in pkg_info['related_dataset']:
            rel_pkg = tk.get_action('package_show')\
                (context, {'id': rd[0]})
            if rel_pkg:
                description += rel_pkg['title'] + '\n'
        description += '\n'

    if pkg_info['tags']:
        description += 'Keywords:\n'
        for kw in pkg_info['tags']:
            description += kw['display_name'] + '\n'
        description += '\n'

    # generating return structures
    mandatory = {'Access Rights': access_rights,
                 'Category': category,
                 'Contributor': contributor,
                 'Created On': created_on,
                 'Data Manager': data_manager,
                 'Description': description,
                 'Journal': journal,
                 'Language': language,
                 'Licence': license,
                 'Rights': rights,
                 'Rights Holder': rights_holder,
                 'Creator': creator,
                 'Subject': subject,
                 'Identifier': identifier,
                 'Title': title}

    optional = {'BibliographicCitation': bibliographic_citation,
                'Geolocation': location,
                'Project': project,
                'Temporal Coverage': temporal_coverage,
                'Publication': citations}  # citations not strictly a part of 'optional'
    hierarchy = {'id': pkg_info['id'],
                 'HasPart': [x['id'] for x in pkg_info['resources']]}

    return \
        {'mandatory': mandatory,
         'optional': optional,
         'hierarchy': hierarchy}, \
        _remove_duplicate(person_ids), \
        _remove_duplicate(org_ids), \
        _remove_duplicate(license_ids), \
        _remove_duplicate(pub_ids)


def _dataformat_text(df_id):
    df = model.Session.query(DataFormat).get(df_id)

    if df is None:
        return '<data format not found>'
    else:
        result = 'Data format name: ' + df.name + '\n'
        if df.is_open:
            result += 'This is an open format.\n'
        else:
            result += 'This is not an open format.\n'

        result += 'Data format description:\n' + df.description + '\n'

        return result


def _category_from_class(classcode):

    # The Sigma2 Category will be set as follows:
    # 1.X.X -> "Observation"
    # 2.X.X -> "Experiment"
    # 3.1.0 -> "Model"
    # 3.2.0 -> "Model"
    # 3.3.X -> "Simulation"
    # 4.X.X -> "Observation"
    # (Valid Sigma2 categories are: Experiment, Observation, Model, Simulation,
    # Software, Image, Calibration)
    classcode = classcode.split('.')
    if classcode[0] == '1':
        return 'Observation'
    elif classcode[0] == '2':
        return 'Experiment'
    elif classcode[0] == '3':
        if classcode[1] == '1' or classcode[1] == '2':
            return 'Model'
        else:
            return 'Simulation'
    else:
        return 'Observation'


def sigma2_dataset_component_metadata(pkg_info, parent_dataset):
    result = []

    components = pkg_info['resources']

    for comp in components:

        child_dataset = deepcopy(parent_dataset)
        child_dataset['hierarchy'] = {
            'id': comp['id'],
            'IsPartOf': parent_dataset['hierarchy']['id']
        }

        # update title with resource name
        title = child_dataset['mandatory']['Title'] + ' - ' + comp['name']

        child_dataset['mandatory']['Title'] = title

        # assemble and update description
        description = comp['description']
        if len(description) > 0:
            description += '\n\n'
        if len(comp['purpose']) > 0:
            description += 'Purpose:\n' + comp['purpose'] + '\n\n'
        if len(comp['assumptions']) > 0:
            description += 'Assumptions:\n' + comp['assumptions'] + '\n\n'
        if len(comp['dataformat']) > 0:
            description += \
                'Data format:\n' + _dataformat_text(comp['dataformat']) + '\n\n'
        category = model.Session.query(ResourceCategory).get(comp['category'])
        if category:
            description += \
                'CO2DataShare category is: \n   ' + \
                category.code + ' : ' + category.title + '\n'


        child_dataset['mandatory']['Description'] = description

        # set more precise category based on data classification
        child_dataset['mandatory']['Category'] = \
            _category_from_class(comp['category'])

        result.append(child_dataset)

    return result


def sigma2_person_metadata(person_ids):

    result = []
    for p_id in person_ids:
        person = model.Session.query(Person).get(p_id)
        if person:
            affiliation = ''
            if len(person.affiliation) > 0:
                # @@ NB: in case of multiple affiliations, only the first one
                # is returned, since only one is supported by Sigma2
                affiliation = person.affiliation[0].display_name

            result.append({'id': p_id,
                           'FirstName': person.first_name,
                           'LastName': person.last_name,
                           'Email': person.email,
                           'OrgShortName': affiliation})
    return result


def sigma2_license_metadata(license_ids):

    result = []
    for l_id in license_ids:
        license = model.Session.query(License).get(l_id)
        if license:
            result.append({'id': l_id,
                           'Access': license.license_url,
                           'Archive': license.license_url,
                           'Name': license.name,
                           'Description': license.description})
    return result


def sigma2_organization_metadata(org_ids):

    result = []
    for o_id in org_ids:
        org = model.Session.query(model.group.Group).get(o_id)
        if org:

            contact_first_name, contact_last_name, contact_email = '', '', ''
            if len(org.contact_person) > 0:
                # if there are multiple contact persons, we can only return the
                # first
                contact_first_name = org.contact_person[0].first_name
                contact_last_name = org.contact_person[0].last_name
                contact_email = org.contact_person[0].email

            result.append({'id': o_id,
                           'OrgLongName': org.display_name,
                           'OrgShortName': org.display_name,
                           'HomePage': org.extra.homepageURL,
                           'ContactFirstName': contact_first_name,
                           'ContactLastName': contact_last_name,
                           'ContactEmail': contact_email})
    return result


def sigma2_publication_metadata(pub_ids):

    result = []
    for p_id in pub_ids:
        pub = model.Session.query(Publication).get(p_id)
        if pub:
            result.append({'id': p_id,
                           'ConferenceCitation': pub.citation,
                           'ConferenceURI': pub.doi,
                           'JournalCitation': pub.citation,
                           'JournalDOI': pub.doi,
                           'Name': pub.name})
    pdb.set_trace()
    return result


def export_package(pkg_name):

    # check credentials
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'for_view': True,
               'auth_user_obj': g.userobj}

    pkg_id = convert_package_name_or_id_to_id(pkg_name, context)
    data_dict = {'id': pkg_id, 'include_tracking': True}

    try:
        tk.check_access('package_update', context, data_dict)
    except logic.NotAuthorized:
        abort(403, ('Not authorized to see this page.'))

    pkg_info = tk.get_action('package_show')(context, {'id': pkg_id})

    upload = upl.get_resource_uploader(pkg_info)

    resource_locations = {res['id']: upload.get_path(res['id'])
                          for res in pkg_info['resources']}

    sigma2_dict = extract_sigma2_metadata(pkg_info)

    landing_page_loc = landing_page_location(pkg_info['name'])
    if not path.isdir(landing_page_loc):
        landing_page_loc = []  # no landing page has been provided

    export_dict = {'pkg_info': pkg_info,
                   'sigma2_metadata': sigma2_dict,
                   'landing_page_location': landing_page_loc,
                   'resource_locations': resource_locations}

    return json.dumps(export_dict, sort_keys=False, indent=4)


class CdsSigma2Plugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer
    def update_config(self, config):
        tk.add_template_directory(config, 'templates/export')

    # IBlueprint
    def get_blueprint(self):

        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates/export'

        blueprint.add_url_rule(u'/export/<pkg_name>',
                               u'export_package',
                               export_package, methods=['GET'])

        return blueprint
