from flask import Blueprint

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import pdb


def custom_action():
    return "Hello World!"


class FrontpagewrapperPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IBlueprint)

    def get_blueprint(self):
        blueprint = Blueprint('foo', self.__module__)
        rules = [
            ('/', 'custom_action', custom_action),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint
    
