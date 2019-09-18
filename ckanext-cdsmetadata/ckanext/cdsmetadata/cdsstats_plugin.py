import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, render_template
import ckan.model as model
from datetime import datetime
from ckan.model import meta, Session
from ckan.model.types import make_uuid
from ckan.common import request, response, g, _
from ckan.logic.converters import convert_package_name_or_id_to_id
from ckan.lib.base import abort, render
import ckan.lib.helpers as h
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
    Column('country', UnicodeText),
    Column('affiliation', UnicodeText),
    Column('date', types.DateTime),
    )

class DatasetStatistics(model.domain_object.DomainObject):
    def __init__(self, user_id, resource_id, country, affiliation):
        self.user_id = user_id
        self.resource_id = resource_id
        self.country = country
        self.affiliation = affiliation
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

        country = request.headers.get('country', u'unspecified')
        affiliation = request.headers.get('affiliation', u'unspecified') or u'unspecified'
        
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

        entry = DatasetStatistics(user_id, resource_id, country, affiliation)
        entry.save()

        return result

    return wrapper


def _compute_stats(context, pkg_id):

    try:
        toolkit.check_access('package_update', context, {'id': pkg_id})
    except logic.NotAuthorized:
        abort(403, _('Not authorized to see this page.'))

    pkg_info = toolkit.get_action('package_show')(context, {'id': pkg_id})

    query = model.Session.query
    overview_stats = []
    resource_user_stats = {}
    resource_country_stats = {}
    resource_affiliation_stats = {}

    # we presume no download found
    first_download_date = None
    
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

        # identify first and last date when resource was downloaded
        first_date = query(func.min(DatasetStatistics.date)).\
                     filter_by(resource_id=res['id']).scalar()
        last_date = query(func.max(DatasetStatistics.date)).\
                    filter_by(resource_id=res['id']).scalar()
        if first_date is not None:
            if not first_download_date or first_date.ctime() < first_download_date:
                first_download_date = first_date.ctime()
        if last_date is not None:
            last_date = last_date.ctime()
            
        overview_stats.append({'name': res['name'],
                               'total': total,
                               'users': users,
                               'anon': anon,
                               'date': last_date})
        try:
            res_name = toolkit.get_action('resource_show')(context, res)['name']
        except:
            res_name = "<missing>"

        unique_user_ids = query(DatasetStatistics.user_id,
                                func.max(DatasetStatistics.date)).\
                          filter_by(resource_id=res['id']).\
                          group_by(DatasetStatistics.user_id).all()
        user_list = []
        for u in unique_user_ids:

            date = None if u[1] is None else u[1].ctime()
            username = "<anonymous/missing>"
            try:
                user = toolkit.get_action('user_show')(context, {'id': u[0]})
                username = user['display_name']
            except logic.NotFound:
                pass
            
            user_list.append({'user': username, 'date': date})

        resource_user_stats[res_name] = user_list

        unique_countries = query(DatasetStatistics.country,
                                 func.count(DatasetStatistics.country),
                                 func.max(DatasetStatistics.date)).\
                                 filter_by(resource_id=res['id']).\
                                 group_by(DatasetStatistics.country).all()
        country_list = []
        for u in unique_countries:
            date = None if u[2] is None else u[2].ctime()
            country = u[0]
            count = u[1]
            country_list.append({'country': country, 'count': count, 'date': date})
        
        resource_country_stats[res_name] = country_list

        unique_affiliations = query(DatasetStatistics.affiliation,
                                    func.count(DatasetStatistics.affiliation),
                                    func.max(DatasetStatistics.date)).\
                                    filter_by(resource_id=res['id']).\
                                    group_by(DatasetStatistics.affiliation).all()
        affiliation_list = []
        for a in unique_affiliations:
            date = None if a[2] is None else a[2].ctime()
            affiliation = a[0]
            count = a[1]
            affiliation_list.append({'affiliation': affiliation,
                                     'count': count, 'date': date})
        resource_affiliation_stats[res_name] = affiliation_list

        
    overview_stats = sorted(overview_stats, key = lambda x: x['name'])
                                   
    return (first_download_date, overview_stats, resource_user_stats,
            resource_country_stats, resource_affiliation_stats)
    

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

    first_date, overview_stats, resource_user_stats, \
        resource_country_stats, resource_affiliation_stats = \
        _compute_stats(context, pkg_id)

    package_dictionary = toolkit.get_action('package_show')(context, data_dict)
    return render(u"package/dataset_statistics_page.html",
                  extra_vars={'pkg_dict': package_dictionary,
                              'first_date': first_date,
                              'overview_stats': overview_stats,
                              'resource_user_stats': resource_user_stats,
                              'resource_affiliation_stats': resource_affiliation_stats,
                              'resource_country_stats': resource_country_stats})

def reset_dataset_statistics(pkg_name):

    context = {'model': model, 'session': model.Session,
               'for_view': True, 'user': g.user, 'auth_user_obj': g.userobj}
    pkg_id = convert_package_name_or_id_to_id(pkg_name, context)
    
    try:
        toolkit.check_access('package_update', context, {'id': pkg_id})
    except logic.NotAuthorized:
        abort(403, _('Not authorized to see this page.'))

    # identify resources for which all entries should be deleted        
    pkg_info = toolkit.get_action('package_show')(context, {'id': pkg_id})
    resources = pkg_info.get('resources', [])
    resource_ids = [x['id'] for x in resources]

    # delete all entries for the concerned resources
    dlt = model.Session.query(DatasetStatistics).\
          filter(DatasetStatistics.resource_id.in_(resource_ids))
    for d in dlt:
        model.Session.delete(d)
    model.Session.commit()
    
    return toolkit.redirect_to(
        h.url_for('cdsstats.show_statistics', pkg_name=pkg_id))

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
        blueprint.add_url_rule(u'/statistics/<pkg_name>',
                               u'show_statistics',
                               show_dataset_statistics, methods=['GET'])
        blueprint.add_url_rule(u'/statistics/reset/<pkg_name>',
                               u'reset_statistics',
                               reset_dataset_statistics, methods=['GET', 'POST'])
        
        return blueprint
    
