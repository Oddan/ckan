import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import ckan.lib.uploader as upl
import ckan.model as model
import ckan.logic as logic
from ckan.lib.base import abort
from ckan.logic.converters import convert_package_name_or_id_to_id
from ckan.common import g
import json
from flask import Blueprint
from os import path
from cdsaccess_plugin import SpecialAccessRights
from plugin import License, Publication
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

    person_ids, org_ids, license_ids, pub_ids = [], [], [], []

    # constant metadata (always the same for export to Sigma2)
    language = 'English'  # always English
    category = 'Observation'  # we use 'Observation' as default.
    journal = ''  # we use BibliographicCitation for citations
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
                (context, {'id': rd})
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

    optional = {'BibliographicCitation': citations,
                'Geolocation': location,
                'Project': project,
                'Temporal Coverage': temporal_coverage}

    return \
        {'mandatory': mandatory, 'optional': optional}, \
        _remove_duplicate(person_ids), \
        _remove_duplicate(org_ids), \
        _remove_duplicate(license_ids), \
        _remove_duplicate(pub_ids)


def sigma2_dataset_component_metadata(pkg_info, parent_dataset):

    # components =  # extract info for components here
    # own_ID = #
    # owner_ID = #
    # part_IDs = # extract IDs from components

    # component_items = {'co2datashare_id' : own_ID,
    #                    'hasPart': part_IDs,
    #                    'isPartOf': owner_ID,
    #                    'components': components}

    pass



def sigma2_person_metadata(person_ids):
    pass


def sigma2_organization_metadata(org_ids):
    pass


def sigma2_license_metadata(license_ids):
    pass




def export_package(pkg_name):

    pdb.set_trace()
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
