import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.lib.base as base
import ckan.model as model
from ckan.common import g, _, session, request
from flask import Blueprint

import pdb

# If this function is used, it prohibits a normal user to access user settings (change password, etc.).
# Only sysadmins will be able to do so.
# This also deactivates and hides the "Manage" button inside the user's profile page.
def user_update(context, data_dict=None):
    return {'success': False, 'msg': 'You are not authorized to update the user profile'}

# If this function is used, it allows users to delete their own profiles
def user_delete(context, data_dict=None):
    
    if data_dict and g.userobj.id == data_dict.get('id', None):
        return {'success': True, 'msg': 'Users allowed to delete their own profile.'}

    return {'success': False, 'msg': 'Users only allowed to delete their own profile.'}

def logout_and_delete():
    # delete user here
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': g.userobj.id}

    # delete user
    try:
        logic.get_action(u'user_delete')(context, data_dict)
    except logic.NotAuthorized:
        msg = _(u'Unauthorized to delete used with id "{user_id}".')
        base.abort(403, msg.format(user_id = g.userobj.id));

    # log out by removing stale cookie (we cannot use repoze.who, likely since user has been deleted)

    response = h.redirect_to(u'user.index')
    for cookie in request.cookies:
        if cookie == u'auth_tkt':
            response.delete_cookie(cookie)
            break

    return response


class Remove_Unwanted_FeaturesPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'remove_unwanted_features')

    # IAuthFunctions

    def get_auth_functions(self):
        return {'user_delete': user_delete}

    # IBlueprint

    def get_blueprint(self):

        blueprint = Blueprint(self.name, self.__module__)
        
        # only use POST method (not GET) method below to avoid accidental user
        # deletion by entering the wrong link
        blueprint.add_url_rule(u'/logout_and_delete', u'logout_and_delete',
                               logout_and_delete, methods=['GET', 'POST'])
        return blueprint
    
