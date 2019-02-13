from sqlalchemy import orm, types, Column, Table, ForeignKey, MetaData
from flask import Blueprint, render_template, render_template_string
import warnings
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.model as model
import ckan.logic as logic
import ckan.exceptions as exceptions
import datetime 

from ckan.controllers.package import PackageController
import ckan.controllers.package

from ckan.common import _, c, request 

from functools import wraps

from pylons import c as pylons_c

import pdb

_package_controller = PackageController()

rights_table_name = 'special_access_rights'
access_restriction_table_name = 'access_restriction'
rights_table = Table(rights_table_name, model.meta.metadata,
                     Column('id', types.UnicodeText, primary_key=True, default=model.types.make_uuid),
                     Column('user_id', types.UnicodeText, ForeignKey('user.id')),
                     Column('package_id', types.UnicodeText, ForeignKey('package.id')))

access_restriction_table = Table(access_restriction_table_name, model.meta.metadata,
                        Column('id', types.UnicodeText, primary_key=True, default=model.types.make_uuid),
                        Column('package_id', types.UnicodeText, ForeignKey('package.id'),
                               unique=True, nullable=False),
                        Column('restricted', types.Boolean, default=False),
                        Column('embargo_date', types.DateTime, default=None))

class SpecialAccessRights(model.domain_object.DomainObject):
    pass
class AccessRestriction(model.domain_object.DomainObject):
    pass

model.meta.mapper(SpecialAccessRights, rights_table,
            properties={ 'user': orm.relation(model.user.User,
                                        backref=orm.backref('special_access_rights',
                                                            cascade='all, delete, delete-orphan')),
                         'package' : orm.relation(model.package.Package,
                                        backref=orm.backref('special_access_rights',
                                                            cascade='all, delete, delete-orphan'))})
model.meta.mapper(AccessRestriction, access_restriction_table,
                  properties={ 'package' : orm.relation(model.package.Package,
                                                        backref=orm.backref('access_restriction',
                                                                            uselist=False))})

orm.configure_mappers() # this will update 'User' and 'Package' with the new relations
# nb: call session.refresh(object) on an object if you want to update its backrefs after a deletion.

@toolkit.auth_allow_anonymous_access
def deny(context, data_dict=None):
    return {'success': False,
            'msg': 'Nobody should have access yet.'}

@toolkit.auth_allow_anonymous_access
def accept(context, data_dict=None):
    return {'success': True}

def is_sysadmin(context):
    user_obj = context.get('auth_user_obj', None)
    if user_obj and user_obj.sysadmin:
        return True
    return False

@toolkit.auth_allow_anonymous_access
def only_admin(context, data_dict=None):
    if is_sysadmin(context):
        return {'success': True}
    return {'success': False,
            'msg': 'Operation only allowed for sysadmin'}

@toolkit.auth_allow_anonymous_access
def everyone(context, data_dict=None):
    return {'success': True}


def check_embargoed(package_id):
    context = {} # since packages are always visible, context does not matter here
    #pdb.set_trace()
    pkg_info = toolkit.get_action('package_show')(context, {'id': package_id})
    embargo_date =  pkg_info.get('embargo_date', None)
    if embargo_date and embargo_date.date() > datetime.date.today():
        return embargo_date
    return None

@toolkit.auth_allow_anonymous_access
def check_resource_restrictions(context, data_dict=None):

    # if the resource's package ID was given directly (e.g. from the
    # 'resources_list.html' snippet), use it directly
    package_id = data_dict.get('package_id', None)

    # if package_id was not provided, use the resource id to determine what the
    # package_id is
    if package_id is None:
        package_id = context['model'].Resource.get(data_dict['id']).package_id
        
    return check_package_restrictions(context, {'package_id' : package_id})

@toolkit.auth_allow_anonymous_access
def check_package_restrictions(context, data_dict=None):

    if "package_id" not in data_dict.keys():
        raise exceptions.CkanException('no package id')
    if data_dict is None:
        raise exceptions.CkanException('no data_dict')

    # check if logged in (if not, then package resources will not be available)
    if context.get('auth_user_obj', None) is None:
        return {'success' : False,
                'msg' : "Dataset resources not available to anonymous users."}
    
    # check if sysadmin (sysadmin has access to everything)
    if is_sysadmin(context):
        return {'success' : True}

    # check if dataset is embargoed (only sysadmin has access)
    package_id = data_dict['package_id']
    pkg_info = toolkit.get_action('package_show')(context, {'id': package_id})
    embargo_date = check_embargoed(package_id)
    if embargo_date:
        return {'success' : False,
                'msg' : "Dataset is under embargo and is scheduled "
                "to be released on: {date}".format(date=embargo_date.date())}
    
    # check if dataset is restricted (only sysadmin and authorized users have access)
    if pkg_info.get('is_restricted', False):
        return {'success' : False,
                'msg' : "Dataset has restricted access."}
    
    # if dataset is neither restricted nor embargoed, everyone has access
    return {'success' : True}


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

    #pdb.set_trace()
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

def grant_rights():

    # allow use of jinja2 template written for pylons
    #c = {'pkg_dict': {}}
    pdb.set_trace()
    return base.render('package/grant_rights.html', {'c' : pylons_c})
    
class CDSCAccessManagementPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    #plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IMiddleware)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)


    # ================================ IBlueprint ================================

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        blueprint.add_url_rule(u'/grant_rights', u'grant_rights', grant_rights)
        return blueprint
    
    # ============================= ITemplateHelpers =============================
    def get_helpers(self):
        return {'check_embargoed' : check_embargoed}
    
    # ================================ IValidators ================================
    # def get_validators(self):
    #     return {'isodate_string': isodate_string}
    
    # ============================== IAuthFunctions ==============================
    
    def get_auth_functions(self):
        return {'package_update': only_admin,
                'package_create': only_admin,
                'package_delete': only_admin,
                'package_show'  : everyone,
                'resource_view_list': everyone,
                'resource_show' : check_resource_restrictions}

    # ================================ IMiddleware ================================
    
    def make_middleware(self, app, config):

        # ensure the patched view is actually served by pylons and not flask
        if not toolkit.check_ckan_version('2.8.2', '2.8.2'):
            raise toolkit.CkanVersionException

        # wrap the 'package' controller in a function that checks access to
        # resources (which is not necessarily the same in our case as the access
        # to the dataset information itself).
        if app.app_name == 'pylons_app':
            ctrl = app.find_controller('package')
            ctrl.resource_read = resource_read_patch(ctrl.resource_read)
        else:
            assert app.app_name == 'flask_app'
        return app

    def make_error_log_middleware(self, app, config):
        return app

    # ================================ IConfigurer ================================
    
    def update_config(self, config):
        #ensure_special_access_table_present()
        toolkit.add_template_directory(config, 'templates')
    
    # =============================== IDatasetForm ===============================
    
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
                          toolkit.get_validator('boolean_validator')],
                          #toolkit.get_validator('ignore_missing')],
        'embargo_date' : [toolkit.get_converter('convert_from_extras'),
                          toolkit.get_validator('isodate'),
                          #toolkit.get_validator('isodate_string'),
                          toolkit.get_validator('ignore_missing')]})
        return schema

    def is_fallback(self):
        # We consider this plugin to be the default handler for package types
        return True

    def package_types(self):
        # This plugin does not handle any special package types, it just acts as
        # a default.
        return []
        
    # def setup_template_variables(self, context, data_dict):
    #     implement_me
    
