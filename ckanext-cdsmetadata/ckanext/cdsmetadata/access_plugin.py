import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import ckan.lib.helpers as h
from flask import Blueprint, render_template

def _user_agreement():
    return render_template(u'user_agreement.html')

class CdsAccessPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer
    def update_config(self, config):
        tk.add_template_directory(config , 'templates/access')

    # IBlueprint
    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_Folder = u'templates/access'

        blueprint.add_url_rule('/user_agreement',
                               u'user_agreement',
                               view_func=_user_agreement)
        return blueprint
