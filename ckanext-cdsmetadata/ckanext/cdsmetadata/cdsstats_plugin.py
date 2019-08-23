import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, render_template
import ckan.model as model
from datetime import datetime
from ckan.model import meta, Session
from ckan.model.types import make_uuid
from ckan.common import request, g

from sqlalchemy import types, Table, Column, ForeignKey, orm, or_
from sqlalchemy.types import UnicodeText, Unicode, Boolean

import pdb
from ckan.common import config
# import ckan.logic as logic

dataset_statistics_table = Table(
    'dataset_statistics', meta.metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('user_id', UnicodeText, ForeignKey('user.id')),
    Column('resource_id', UnicodeText, ForeignKey('resource.id')),
    Column('date', types.DateTime),
    )

class DatasetStatistics(model.domain_object.DomainObject):
    def __init__(self, user_id, resource_id):
        self.user_id = user_id
        self.resource_id = resource_id
        self.date = datetime.now()
        
meta.mapper(DatasetStatistics, dataset_statistics_table,
    properties={
        'user': orm.relation(model.user.User,
                        backref=orm.backref('downloads',
                                            cascade='save-update, merge')),
        'resource': orm.relation(model.resource.Resource,
                        backref=orm.backref('downloads',
                                            cascade='save-update, merge'))}
)

if not dataset_statistics_table.exists():
    dataset_statistics_table.create()
            
def resource_download_patch(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):

        result = fn(*args, **kwargs)

        if (result_is_ok):
            register_download()

        return result

    return wrapper


# This function gets called when a request to show dataset statistics is received
def show_dataset_statistics(pkg_name):
    #pdb.set_trace()
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
    plugins.implements(plugins.IMiddleware)

    # IMiddleware
    def make_middleware(self, app, config):

        # ensure the patched view is actually served by pylons and not flask
        if not toolkit.check_ckan_version('2.8.2', '2.8.2'):
            raise toolkit.CkanVersionException

        # wraps the package download function in a function that updates statistics
        if app.app_name == 'pylons_app':
            ctrl = app.find_controller('package')
            ctrl.resource_download = \
                resource_download_patch(ctrl.resource_download)
        else:
            assert app.app_name == 'flask_app'

        return app

    def make_error_log_middleware(self, app, config):
        return app

        
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
    
