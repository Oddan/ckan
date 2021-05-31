import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import ckan.lib.uploader as upl
import ckan.model as model
import ckan.logic as logic
from ckan.lib.base import abort
from ckan.logic.converters import convert_package_name_or_id_to_id
from ckan.common import g, config, request
from ckan.lib.base import render
import json
from copy import deepcopy
from flask import Blueprint
from os import path
import shutil
from cdsaccess_plugin import SpecialAccessRights
from resource_category import ResourceCategory
from plugin import License, Publication, DataFormat, Person
from landing_page_plugin import landing_page_location
import requests
import pprint
import copy
from utils.Sigma2MetadataObjects import classdict as mdclasses

import pdb

def users_with_access(pkg_id):
    return [usr.id for usr in model.Session.query(SpecialAccessRights).
            filter(SpecialAccessRights.package_id == pkg_id).all()]


def extract_sigma2_metadata(pkg_info):

    datasets, person_ids, org_ids, license_ids, pub_ids =\
        sigma2_dataset_metadata(pkg_info)

    return {'datasets': datasets,
            'persons': sigma2_person_metadata(person_ids),
            'publications': sigma2_publication_metadata(pub_ids),
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
    description = pkg_info.get('notes', '<empty>')
    title = pkg_info.get('title', '<empty>')
    identifier = pkg_info.get('doi', '<empty>')
    created_on = pkg_info.get('metadata_created', '<empty>')
    location = pkg_info.get('location', '<empty>')

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

    # set license and rights (url to license)
    license = pkg_info.get('cdslicense')
    rights = ''
    if license:
        license_ids.append(license)
        lobj = model.Session.query(License).get(pkg_info['cdslicense'])
        if lobj:
            rights = lobj.license_url

    # citations
    citations = [{'id': x[0], 'title': x[1]} for x in pkg_info['publications']]
    pub_ids.extend([x[0] for x in pkg_info['publications']])

    # temporal coverage
    temporal_coverage = [pkg_info.get('temporal_coverage_start'),
                         pkg_info.get('temporal_coverage_end')]

    # information fields to add to 'description'
    if len(description) > 0:
        # separate new content from existing by adding a couple of lines
        description += '\n\n\n'

    description += 'Project type: ' + pkg_info.get('project_type', '<empty>') + '\n\n'

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
        if comp.get('dataformat'):
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

            contact_first_name, contact_last_name = '', ''
            contact_email, contact_id = '', ''
            if len(org.contact_person) > 0:
                # if there are multiple contact persons, we can only return the
                # first
                contact_first_name = org.contact_person[0].first_name
                contact_last_name = org.contact_person[0].last_name
                contact_email = org.contact_person[0].email
                contact_id = org.contact_person[0].id

            result.append({'id': o_id,
                           'OrgLongName': org.display_name,
                           'OrgShortName': org.display_name,
                           'HomePage': org.extra.homepageURL,
                           'ContactID': contact_id,
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
    return result


def _create_upload_header(token):
    return {'accept': 'application/json',
            'Authorization': 'Bearer ' + token['access_token'],
            'content-type': 'application/json'}


def _ensure_entities_exist(token, api_url,
                           null_for_search_fields, entity_list,
                           upload_json_fun=lambda x: x.toJSON()):

    headers = _create_upload_header(token)

    for entity in entity_list:
        search_entity = copy.deepcopy(entity)
        for f in null_for_search_fields:
            setattr(search_entity, f, "")
        arglist = '&'.join(['{x}={xval}'.format(x=x,
                                                xval=getattr(search_entity, x))
                            for x in entity.metadataFields()])

        exist_check = requests.get(api_url + "?" + arglist, headers=headers)
        requests.Response.raise_for_status(exist_check)  # throw if not 200

        if not exist_check.json()['registered']:
            r = requests.post(api_url, upload_json_fun(entity),
                              headers=headers)
            requests.Response.raise_for_status(r)


def _make_mdperson(pdata):
    return mdclasses['Person'](firstname=pdata['FirstName'],
                               lastname=pdata['LastName'],
                               email=pdata['Email'],
                               federatedid=pdata['Email'])


def _make_mdorganization(odata):
    return mdclasses['Organization'](shortname=odata['OrgShortName'],
                                     longname=odata['OrgLongName'],
                                     contactemail=odata['ContactEmail'],
                                     homepage=odata['HomePage'])


def _ensure_persons_exist(token, archive_url, persons):

    plist = [_make_mdperson(p) for p in persons]
    _ensure_entities_exist(token, archive_url + '/api/person/',
                           ['federatedid'],
                           plist)
    return plist


def _ensure_organizations_exist(token, archive_url, persons, orgs):

    odict = {_make_mdorganization(o):
             filter(lambda x: x['id'] == o['ContactID'], persons)
             for o in orgs}

    def _org_upload_json(org, odict=odict):
        # generate the json object needed for the api to create an organization
        if len(odict[org]) == 0:
            raise Exception('Organization has no contact person.')
        else:
            person = odict[org][0]  # if multiple, use the first one
        return '{' + '"organization": {}, "person": {}'.format(
            org.toJSON(),
            _make_mdperson(person).toJSON()) + '}'

    olist = odict.keys()
    _ensure_entities_exist(token, archive_url + '/api/organization/',
                           [], olist, _org_upload_json)
    return olist


def _ensure_licenses_exists(token, archive_url, licenses):
    # @@ IMPLEMENT ME
    # (api functionality not yet ready)
    pass


def _send_off_manifest(token, resource_locations, lpage_zipfile_location):
    # @@ IMPLEMENT ME
    # (api functionality not yet ready)
    pass


def _prepare_dataset_api_metadata(sigma2data):
    # @@ IMPLEMENT ME
    pass


def _landing_page_zipfile_location(landing_page_location):
    pdb.set_trace()
    if not landing_page_location:
        # no landing page defined
        return

    dirname = path.dirname(path.normpath(landing_page_location))
    bname = path.basename(path.normpath(landing_page_location))

    target_location = path.join(dirname, bname + '.zip')

    if not path.isfile(target_location):
        # zipfile does not yet exist, create it.
        shutil.make_archive(path.normpath(landing_page_location),
                            'zip',
                            path.normpath(landing_page_location))

    return target_location


def _upload_procedure(token, archive_url, export_dict):

    s2data = export_dict['sigma2_metadata']

    # ensure existence of persons
    _ensure_persons_exist(token, archive_url, s2data['persons'])

    # ensure existence of organiations
    _ensure_organizations_exist(token, archive_url,
                                s2data['persons'],
                                s2data['organizations'])

    # ensure existence of licence
    _ensure_licenses_exists(token, archive_url, s2data['licenses'])

    # prepare API metadata object for full dataset
    dataset_api_mdata = \
        _prepare_dataset_api_metadata(export_dict['sigma2_metadata'])

    # upload API metadata object
    # r = requests.post(archive_url + '/api/dataset/',
    #                   dataset_api_mdata.toJSON(),
    #                   headers=_create_upload_header(token))
    # requests.Response.raise_for_status(r)

    # ensure landing page is zipped, and get its location
    lpage_zipfile_loc = \
        _landing_page_zipfile_location(export_dict['landing_page_location'])

    # send off manifest file to initiate full dataset transfer
    _send_off_manifest(token,
                       export_dict['resource_locations'], lpage_zipfile_loc)


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

    # get the package information object
    pkg_info = tk.get_action('package_show')(context, {'id': pkg_id})

    # determine location of dataset components on local disk
    upload = upl.get_resource_uploader(pkg_info)

    resource_locations = {res['id']: upload.get_path(res['id'])
                          for res in pkg_info['resources']}

    # extract metadata for Sigma2 from the package object
    sigma2_dict = extract_sigma2_metadata(pkg_info)

    # determine the location of the landing page
    landing_page_loc = landing_page_location(pkg_info['name'])
    if not path.isdir(landing_page_loc):
        landing_page_loc = []  # no landing page has been provided

    # organize all info to send to Sigma2 as a dictionary
    export_dict = {'pkg_info': pkg_info,
                   'sigma2_metadata': sigma2_dict,
                   'landing_page_location': landing_page_loc,
                   'resource_locations': resource_locations}

    if request.method == 'POST':
        # user has confirmed.  Now send off

        error_msg = []
        try:
            # get token
            archive_url = config.get('ckan.cdsmetadata.sigma2_archive_url')
            token_url = archive_url + '/token'
            username = config.get('ckan.cdsmetadata.sigma2_archive_username')
            password = config.get('ckan.cdsmetadata.sigma2_archive_password')

            headers = {'content-type': 'application/x-www-form-urlencoded',
                       'accept': 'application/json'}
            data = {'grant_type': [], 'username': username,
                    'password': password,
                    'scope': [], 'client_id': [], 'client_secret': []}
            res = requests.post(token_url, headers=headers, data=data)

            token = json.loads(res.content)

            # upload data
            _upload_procedure(token, archive_url, export_dict)
        except requests.exceptions.RequestException as e:
            error_msg = "Unable to communicate with server: {0}".format(e)
        except ValueError as e:
            error_msg = "JSON parse error occurred: {0}".format(e)
        except Exception as e:
            error_msg = "An unknown error occurred: {0}".format(e)

        if error_msg:
            return render(u'confirmation.html',
                          extra_vars={'export_dict': export_dict,
                                      'error_msg': error_msg})
        else:
            msg = 'Upload succeeded'
            return render(u'success.html',
                          extra_vars={'message': msg})

    else:
        # show data and ask for confirmation
        pp = pprint.PrettyPrinter(indent=2)
        pretty_printed_dict = pp.pformat(export_dict['sigma2_metadata'])

        return render(u'confirmation.html',
                      extra_vars={'export_dict': export_dict,
                                  'pretty_print': pretty_printed_dict})


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
                               export_package, methods=['GET', 'POST'])

        return blueprint
