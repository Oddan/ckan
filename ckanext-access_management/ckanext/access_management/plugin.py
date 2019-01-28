from sqlalchemy import orm, types, Column, Table, ForeignKey, MetaData
from flask import Blueprint
import warnings
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.model as model
import ckan.logic as logic
import ckan.exceptions as exceptions

from ckan.controllers.package import PackageController
import ckan.controllers.package

from ckan.common import _, c, request 

from functools import wraps


import pdb

_package_controller = PackageController()

rights_table_name = 'special_access_rights'
rights_table = Table(rights_table_name, model.meta.metadata,
                     Column('id', types.UnicodeText, primary_key=True, default=model.types.make_uuid),
                     Column('user_id', types.UnicodeText, ForeignKey('user.id')),
                     Column('package_id', types.UnicodeText, ForeignKey('package.id')))

class SpecialAccessRights(model.domain_object.DomainObject):
    pass
model.meta.mapper(SpecialAccessRights, rights_table,
                  properties={ 'user': orm.relation(model.user.User),
                               'package' : orm.relation(model.package.Package)})

@toolkit.auth_allow_anonymous_access
def deny(context, data_dict=None):
    return {'success': False,
            'msg': 'Nobody should have access yet.'}

@toolkit.auth_allow_anonymous_access
def accept(context, data_dict=None):
    return {'success': True}

@toolkit.auth_allow_anonymous_access
def only_admin(context, data_dict=None):

    if context.get('user') == 'admin':
        return {'success': True}

    return {'success': False,
            'msg': 'Operation only allowed for admin'}

@toolkit.auth_allow_anonymous_access
def everyone(context, data_dict=None):
    return {'success': True}

def resource_read_patch(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        # check access, forward to controller if OK
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        id = kwargs.get('id', None)
        resource_id = kwargs.get('resource_id', None)

        try:
            logic.check_access('resource_show', context, {'id': resource_id})
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to access this resource.'))
        
        return function(*args, id=id, resource_id=resource_id)
    return wrapper
    
def _modify_package_schema(schema):
    schema.update({
        'is_restricted': [toolkit.get_validator('ignore_missing'),
                          toolkit.get_validator('boolean_validator'),
                          toolkit.get_converter('convert_to_extras')],
        'embargo_date' : [toolkit.get_validator('ignore_missing'),
                          toolkit.get_validator('isodate'),
                          toolkit.get_converter('convert_to_extras')]
    })
    
    return schema

def ensure_special_access_table_present():
    tmp_metadata = MetaData(model.meta.metadata.bind)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', '.*(reflection|tsvector).*')
        tmp_metadata.reflect()

    pdb.set_trace()
    if ((not rights_table_name in tmp_metadata.tables.keys()) or
        (tmp_metadata.tables[rights_table_name].c.keys() !=
         model.meta.metadata.tables[rights_table_name].c.keys())):
        raise exceptions.CkanConfigurationException(
            '''Database not properly set up.

            The special user rights table needs to be included in the database.
            In order to create it, copy the file migration/XXX_add_special_rights_table.py
            to the ckan/migration/versions folder and substitute XXX by the new revision number. 
            
            Then run paster db upgrade.
            '''
            )
    
    pdb.set_trace()

class CDSCAccessManagementPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IMiddleware)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)

    def create_package_schema(self):
        schema = super(CDSCAccessManagementPlugin, self).create_package_schema()
        schema = _modify_package_schema(schema)
        return schema
        
    def update_package_schema(self):
        schema = super(CDSCAccessManagementPlugin, self).update_package_schema()
        schema = _modify_package_schema(schema)
        return schema
        
    def show_package_schema(self):
        schema = super(CDSCAccessManagementPlugin, self).show_package_schema()
        schema.update({
        'is_restricted': [toolkit.get_converter('convert_from_extras'),
                          toolkit.get_validator('boolean_validator'),
                          toolkit.get_validator('ignore_missing')],
        'embargo_date' : [toolkit.get_converter('convert_from_extras'),
                          toolkit.get_validator('isodate'),
                          toolkit.get_validator('ignore_missing')]})
        return schema

    def is_fallback(self):
        # We consider this plugin to be the default handler for package types
        return True

    def package_types(self):
        # This plugin does not handle any special package types, it just acts as
        # a default.
        return []
        
    def update_config(self, config):
        ensure_special_access_table_present()
        
        toolkit.add_template_directory(config, 'templates')
    
    def make_middleware(self, app, config):

        # ensure the patched view is actually served by pylons and not flask
        if not toolkit.check_ckan_version('2.8.2', '2.8.2'):
            raise toolkit.CkanVersionException
        if app.app_name == 'pylons_app':
            ctrl = app.find_controller('package')
            ctrl.resource_read = resource_read_patch(ctrl.resource_read)
        else:
            assert app.app_name == 'flask_app'
        return app

    def make_error_log_middleware(self, app,config):
        return app
    
    def get_auth_functions(self):
        return {'package_update': only_admin,
                'package_create': only_admin,
                'package_delete': only_admin,
                'package_show'  : everyone,
                'resource_view_list': everyone,
                'resource_show' : only_admin}


    
