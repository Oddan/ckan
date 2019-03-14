import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, request, render_template


get_agreement = Blueprint('get_agreement', __name__)
get_agreement.template_folder = u'templates'

@get_agreement.route('/agreement', methods=['GET'])
def show_agreement():
    return render_template(u"agreements.html", agreement_name=request.args['agreement_name'])




class User_RegistrationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'user_registration')


    # IBlueprint

    def get_blueprint(self):
        u'''Return a Flask Blueprint object to be registered by the app.'''

        # Create Blueprint for plugin
        #blueprint = Blueprint(self.name, self.__module__)
        #blueprint.template_folder = u'templates'
        # Add plugin url rules to Blueprint object
        #rules = [
        #    (u'/agreement/', u'agreement', show_agreement(agreement_name)),
        #]
        #for rule in rules:
        #    blueprint.add_url_rule(*rule)

        #return blueprint
        return get_agreement