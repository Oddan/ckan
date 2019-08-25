import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, render_template
import ckan.model as model
from datetime import datetime
from ckan.model import meta, Session
from ckan.model.types import make_uuid
from ckan.common import request, g, _
from ckan.logic.converters import convert_package_name_or_id_to_id
from ckan.lib.base import abort, render
from sqlalchemy import func, distinct, types, Table, Column, ForeignKey, orm, or_
from sqlalchemy.types import UnicodeText, Unicode, Boolean
import ckan.logic as logic

from functools import wraps

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
        
        resource_id = kwargs['resource_id']
        package_id = \
            toolkit.get_action('resource_show')(
                {'model': model, 'user': g.user, 'auth_user_obj': g.userobj},
                {'id': resource_id}
            )['package_id']

        result = fn(args[0], id=package_id, resource_id=resource_id)

        # recording the download
        user_id = None
        if g.userobj:
            #@@ doesn't work'
            user_id = g.userobj.id

        entry = DatasetStatistics(user_id, resource_id)
        entry.save()

        return result

    return wrapper


def _compute_stats(context, pkg_id):

    pkg_info = toolkit.get_action('package_show')(context, {'id': pkg_id})

    query = model.Session.query
    overview_stats = []
    resource_stats = {}
    for res in pkg_info['resources']:

        # count total downloads of this resource
        total = query(DatasetStatistics).filter_by(resource_id=res['id']).count()

        # count unique users that downloaded this resource
        users = query(func.count(distinct(DatasetStatistics.user_id))).\
                filter_by(resource_id=res['id']).scalar()

        # count anonymous downloads (should usually be zero)
        anon = query(DatasetStatistics).\
               filter_by(resource_id=res['id']).\
               filter_by(user_id=None).count()

        # identify last date when resource was downloaded
        last_date = query(func.max(DatasetStatistics.date)).\
                    filter_by(resource_id=res['id']).scalar()

        overview_stats.append({'name': res['name'],
                               'total': total,
                               'users': users,
                               'anon': anon,
                               'date': last_date.ctime()})
        try:
            res_name = toolkit.get_action('resource_show')(context, res)['name']
        except:
            res_name = "<missing>"

        unique_users = query(DatasetStatistics.user).\
                       filter_by(resource_id=res['id']).\
                       group_by(DatasetStatistics.user).all()
        
        user_list = [{'user': user, 'date': 'date'} for user in unique_users]
                    
        resource_stats[res_name] = user_list
        
    overview_stats = sorted(overview_stats, key = lambda x: x['name'])
                                   
    return (overview_stats, resource_stats)
    

# This function gets called when a request to show dataset statistics is received
def show_dataset_statistics(pkg_name):

    context = {'model': model, 'session': model.Session,
               'user': g.user, 'for_view': True,
               'auth_user_obj': g.userobj}

    pkg_id = convert_package_name_or_id_to_id(pkg_name, context)
    data_dict = {'id': pkg_id, 'include_tracking': True}

    try:
        toolkit.check_access('package_update', context, data_dict)
    except logic.NotAuthorized:
        abort(403, _('Not authorized to see this page.'))

    overview_stats, resource_stats = _compute_stats(context, pkg_id)

    package_dictionary = toolkit.get_action('package_show')(context, data_dict)
    return render(u"package/dataset_statistics_page.html",
                  extra_vars={'pkg_dict': package_dictionary,
                              'overview_stats': overview_stats,
                              'resource_stats': resource_stats})


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
    
