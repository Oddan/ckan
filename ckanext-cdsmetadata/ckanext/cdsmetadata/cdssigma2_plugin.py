import ckan.plugins as plugins
import ckan.lib.helpers as h
import ckan.plugins.toolkit as tk
import ckan.lib.uploader as upl
from flask import Blueprint

import pdb


def export_package(pkg_name):

    # check credentials
    return "Hello world"
    # identify location of all package resources



class CdsSigma2Plugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    # plugins.implements(plugins.IResourceController)

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




    
    # def before_create(self, context, resource):
    #     pass
    
    # def after_create(self, context, resource):
    #     upload = upl.get_resource_uploader(resource)
    #     filepath = upload.get_path(resource['id'])
    #     #pdb.set_trace()
    #     pass

    # def before_update(self, context, current, resource):
    #     pass
    
    # def after_update(self, context, resource):
    #     pass

    # def before_delete(self, context, resource, resources):
    #     pass

    # def after_delete(self, context, resources):
    #     pass
    
    # def before_show(self, resource_dict):
    #     pass
