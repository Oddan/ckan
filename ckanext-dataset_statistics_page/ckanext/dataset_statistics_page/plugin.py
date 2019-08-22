import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint,  request, render_template
import re
import ckan.model as model
from ckan.common import c
import ckan.logic as logic
import pdb


# This function gets called when a request to show dataset statistics is received
def show_dataset_statistics():
    context = {'model': model, 'session': model.Session,
                   'user': c.user, 'for_view': True,
                   'auth_user_obj': c.userobj}
    dataset_name = request.values["id"]
    data_dict = {'id': dataset_name, 'include_tracking': True}
    package_dictionary = logic.action.get.package_show(context, data_dict)
    return render_template(u"package/dataset_statistics_page.html", pkg_dict = package_dictionary)




class Dataset_Statistics_PagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IRoutes)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'dataset_statistics_page')

    
    # IBlueprint

    def get_blueprint(self):

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        # Add plugin url rules to Blueprint object
        rules = [
            (u'/statistics', u'show_statistics', show_dataset_statistics),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule, methods=['GET'])

        return blueprint


    # IRoutes

    def before_map(self, map):
        map.connect('show_statistics', '/statistics',
                    action='show_statistics', controller='package')
        return map

    def after_map(self, map):
        return map