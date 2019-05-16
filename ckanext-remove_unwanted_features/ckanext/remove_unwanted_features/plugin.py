import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.lib.base as base
import ckan.model as model
import re
from ckan.common import g, _, request
from flask import Blueprint
from pylons.controllers.util import redirect as pylons_redirect
from pylons.controllers.util import abort as pylons_abort
from flask import abort as flask_abort


import pdb


# If this function is used, it prohibits a normal user to access user settings
# (change password, etc.).  Only sysadmins will be able to do so.  This also
# deactivates and hides the "Manage" button inside the user's profile page.
def user_update(context, data_dict=None):
    return {'success': False,
            'msg': 'You are not authorized to update the user profile'}


# If this function is used, it allows users to delete their own profiles
def user_delete(context, data_dict=None):

    if data_dict and g.userobj.id == data_dict.get('id', None):
        return {'success': True,
                'msg': 'Users allowed to delete their own profile.'}

    return {'success': False,
            'msg': 'Users only allowed to delete their own profile.'}


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
        base.abort(403, msg.format(user_id=g.userobj.id))

    # log out by removing stale cookie (we cannot use repoze.who, likely since
    # user has been deleted)

    response = h.redirect_to(u'/')
    for cookie in request.cookies:
        if cookie == u'auth_tkt':
            response.delete_cookie(cookie)
            break

    return response


def _check_if_override(rule_str, args):

    # Format for overrides: (include_sysadmin, regex, redirect, redirect args)
    # If redirect is missing, it means a simple block.

    overrides = {(False, u'^/user/$', None, None),
                 (True, u'^/user/<id>', u'/user/edit/{0}', ('id',))}

    sysadmin = g.userobj and g.userobj.sysadmin

    for elem in overrides:
        if elem[0] or not sysadmin:
            if re.search(elem[1], rule_str):
                # we should override this rule
                if elem[2] is None:
                    # block this rule
                    return -1
                else:
                    # redirect this rule
                    argvals = (args[a] for a in elem[3])
                    redir = elem[2].format(*argvals)
                    return redir

    # if rule_str == u'/user/' and not sysadmin:
    #     return -1  # abort
    # elif rule_str == u'/user/<id>':
    #     return u'/user/edit/' + args['id']


class Remove_Unwanted_FeaturesPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IMiddleware)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'remove_unwanted_features')

    # IAuthFunctions

    def get_auth_functions(self):
        return {'user_delete': user_delete}

    # IMiddleware

    def _flask_routing_override(self):

        rule_str = request.url_rule.rule
        args = request.view_args

        action = _check_if_override(rule_str, args)
        if action:
            if action == -1:  # abort
                flask_abort(404, "Not found")
            else:
                return h.redirect_to(action)
        pass

    def _pylons_override_before(self, controller):

        super_fun = controller.__before__
        
        def _before(slf, action, **params):
            super_fun(slf, action, **params)
            #pdb.set_trace()
            #pylons_redirect("http://google.com")
            #pdb.set_trace()

        return _before

    def make_middleware(self, app, config):
        #pdb.set_trace()
        if app.app_name == 'pylons_app':
            #pdb.set_trace()
            base.BaseController.__before__ = self._pylons_override_before(base.BaseController)
            self.pylons_app = app
        else:
            # add override (will come in addition to overrides already in
            # place)
            app.before_request(self._flask_routing_override)
            self.flask_app = app

        return app
    
    # IBlueprint

    def get_blueprint(self):

        #pdb.set_trace()
        blueprint = Blueprint(self.name, self.__module__)

        # only use POST method (not GET) method below to avoid accidental user
        # deletion by entering the wrong link
        blueprint.add_url_rule(u'/logout_and_delete', u'logout_and_delete',
                               logout_and_delete, methods=['POST'])

        # rules to override existing rules, in order to remove functionality
        #blueprint.add_url_rule(u'/user', u'user_overrride', self._user_override)
        
        return blueprint

