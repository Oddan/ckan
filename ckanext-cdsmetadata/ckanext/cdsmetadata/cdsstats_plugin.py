import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, render_template
import ckan.model as model
from ckan.common import request, g
# import ckan.logic as logic

# This function gets called when a request to show dataset statistics is received
def show_dataset_statistics(pkg_name):
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'for_view': True,
               'auth_user_obj': g.userobj}
    #dataset_name = request.values["id"]
    #data_dict = {'id': dataset_name, 'include_tracking': True}
    data_dict = {'id': pkg_name, 'include_tracking': True}
    
    package_dictionary = toolkit.get_action('package_show')(context, data_dict)
    return render_template(u"package/dataset_statistics_page.html",
                           pkg_dict=package_dictionary)


class CdsStatsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer
    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates/stats')

    # IBlueprint
    def get_blueprint(self):

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates/stats'

        # Add plugin url rules to Blueprint object
        rules = [
            (u'/statistics/<pkg_name>', u'show_statistics', show_dataset_statistics),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule, methods=['GET'])

        return blueprint
    
