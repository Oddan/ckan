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

import pdb

def extract_sigma2_metadata(pkg_info):

    # mandatory metadata
    description = pkg_info['notes']
    title = pkg_info['title']
    rights_holder = pkg_info.get('organization')
    if rights_holder:
        rights_holder = rights_holder['title']
    identifier = pkg_info['doi']
    language = 'English'  # always English
    access_rights = ''
    category = ''
    contributor = ''
    created_on = ''
    creator = ''
    data_manager = ''
    journal = ''
    license = ''
    rights = ''
    subject = 'geological CO2 storage'  # always, for now

    mandatory_items = {'Access Rights': access_rights,
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
    return mandatory_items


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

    export_dict = {'pkg_info': pkg_info,
                   'sigma2_metadata': sigma2_dict,
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
