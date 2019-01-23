from flask import Blueprint
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.model as model
import ckan.logic as logic

from ckan.controllers.package import PackageController
import ckan.controllers.package

from ckan.common import _, c, request 

from functools import wraps

import pdb

_package_controller = PackageController()

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

# #def resource_read_wrapper(context, data_dict):
# def resource_read_wrapper(id, resource_id):    
#     '''
#     Wrapper function to ensure a user has the right to view a resource before
#     letting him/her view its presentational page.
#     '''
#     context = {'model': model, 'session': model.Session,
#                'user': c.user, 'auth_user_obj': c.userobj}
#     try:
#         logic.check_access('resource_show', context, {'id': resource_id})
#     except logic.NotAuthorized:
#         base.abort(403, _('Unauthorized to access this resource.'))

#     return _package_controller.resource_read(id, resource_id)
#     # return h.redirect_to(controller='package', action='resource_read',
#     #                      id=id, resource_id=resource_id)

#     #return u'Hello World'

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
    
    
class CDSCAccessManagementPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IMiddleware)

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


    # def get_blueprint(self):
    #     u'''Return a blueprint for views that need to be overridden.'''
    #     blueprint = Blueprint(self.name, self.__module__)
    #     blueprint.add_url_rule(u'/dataset/<id>/resource/<resource_id>',
    #                            u'resource_read',
    #                            resource_read_wrapper)
    #     return blueprint
    
    
