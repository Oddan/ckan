import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.lib.base as base
import ckan.model as model
import re
from ckan.common import g, _, request, is_flask_request
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


# Format for overrides: (include_sysadmin, regex, redirect, redirect args) If
# redirect is missing, it means access should simply be blocked.  For pages
# served by Pylons, there are additional two fields stating the name of the
# _action_ and the _controller_ involved.  These are necessary since orders
# matters in the Pylons routing table (e.g. 'dataset/new' is chosen over
# 'dataset/action'), meaning that a simple regex is not always enough to
# uniquely determine what page/resource refers to.

# NB: To get a list of all routepaths in pylons, you can use the following
# command:  [a.routepath for a in ckan.common.config['routes.map'].matchlist]
_rc = re.compile

_flask_overrides = [
    (True, _rc(u'^/dashboard/?.*$'), u'/', None),
    (True, _rc(u'^/feeds/?.*$'), None, None),
    (True, _rc(u'^/hello/?$'), u'/', None),
    (False, _rc(u'^/user/?$'), u'/user/edit/', None),
    (True, _rc(u'^/user/activity/.*'), None, None),
    (True, _rc(u'^/user/<id>'), u'/user/edit/{0}', ('id',)),
    (True, _rc(u'^/user/register'), u'/registration_closed', None),
    (False, _rc(u'^/api(/.*)?/action/.*$'), None, None) # disable action API except for admin
]
_pylons_overrides = [
    (True, _rc(u'^/dataset(/[^/]*)?(/.*)?$'), None, None, 'list', 'package'),
    (True, _rc(u'^/group/?$'), None, None),
    (True, _rc(u'^/groups/?$'), None, None),
    (True, _rc(u'^/dataset/followers/.*'), None, None),
    (True, _rc(u'^/dataset/activity/.*'), None, None),
    (True, _rc(u'^/dataset/groups/.*'), None, None),
    (True, _rc(u'^/revision.*'), None, None),
]


def registration_closed_message():
    message = 'Registration currently limited to test users.  \
    If you are interested in becoming a test user, please contact CO2 \
    DataShare administrator.'
    
    return base.render(u'error_document_template.html',
                       {'code': [], u'content': message})


def _check_if_override():
    #pdb.set_trace()
    if is_flask_request():
        rule_str = request.url_rule.rule
        args = request.view_args
        overrides = _flask_overrides
    else:
        rule_str = request.urlargs.current()
        args = request.urlvars
        overrides = _pylons_overrides

    sysadmin = g.userobj and g.userobj.sysadmin

    for elem in overrides:
        if elem[0] or not sysadmin:
            if elem[1].match(rule_str):

                # do not override if pylons has assigned a different
                # action/controller to this particular url
                if not is_flask_request() and len(elem) > 4:
                    if args['action'] and elem[4] != args['action']:
                        # do not override if specified action does not match
                        continue
                    elif args['controller'] and elem[5] != args['controller']:
                        # do not override if specified controller doesn't match
                        continue

                # we should override this rule

                if elem[2] is None:
                    # block this rule
                    return -1
                else:
                    # redirect this rule
                    try:
                        argvals = ()
                        if elem[3]:
                            argvals = (args[a] for a in elem[3])
                        redir = elem[2].format(*argvals)
                    except TypeError:
                        # something went wrong (likely a missing argument).  In
                        # this case, redirect to front page
                        redir = '/'
                    return redir



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

    def _routing_override(self):

        action = _check_if_override()
        if action:
            if action == -1:  # abort
                base.abort(404, "Not found")
            else:
                return h.redirect_to(action)
        pass

    def _pylons_override_before(self, controller):

        super_fun = controller.__before__

        def _before(slf, action, **params):
            super_fun(slf, action, **params)
            #pdb.set_trace()
            self._routing_override()

        return _before

    def make_middleware(self, app, config):

        if app.app_name == 'pylons_app':

            base.BaseController.__before__ = \
                self._pylons_override_before(base.BaseController)
            self.pylons_app = app
        else:
            # add override (will come in addition to overrides already in
            # place)
            app.before_request(self._routing_override)
            self.flask_app = app

        return app

    def make_error_log_middleware(self, app, config):
        return app
    
    # IBlueprint

    def get_blueprint(self):

        blueprint = Blueprint(self.name, self.__module__)

        # only use POST method (not GET) method below to avoid accidental user
        # deletion by entering the wrong link
        blueprint.add_url_rule(u'/logout_and_delete', u'logout_and_delete',
                               logout_and_delete, methods=['POST'])

        # rules to override existing rules, in order to remove functionality
        # blueprint.add_url_rule(u'/user', u'user_overrride',
        # self._user_override)

        blueprint.add_url_rule(u'/registration_closed', u'registration_closed',
                               registration_closed_message)

        return blueprint
