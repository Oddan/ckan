import ckan.plugins as plugins
import ckan.lib.helpers as h
import ckan.plugins.toolkit as tk
from ckan.common import g, request, is_flask_request
import ckan.lib.base as base

import re

# plugin to modify portal presentation and suppress unneeded features

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
    # (True, _rc(u'^/user/register'), u'/registration_closed', None),
    (False, _rc(u'^/api(/.*)?/action/.*$'), None, None)  # disable action API
]                                                        # except for admin
_pylons_overrides = [
    (True, _rc(u'^/dataset(/[^/]*)?(/.*)?$'), None, None, 'list', 'package'),
    (True, _rc(u'^/group/?$'), None, None),
    (True, _rc(u'^/groups/?$'), None, None),
    (True, _rc(u'^/dataset/followers/.*'), None, None),
    (True, _rc(u'^/dataset/activity/.*'), None, None),
    (True, _rc(u'^/dataset/groups/.*'), None, None),
    (True, _rc(u'^/revision.*'), None, None),
]


def _check_if_override():
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


def _datasets_list():
    return tk.get_action('current_package_list_with_resources')(
        data_dict={'limit': 5}
    )


class CdsThemePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IMiddleware)

    # IConfigurer
    def update_config(self, config):
        tk.add_public_directory(config, 'public')
        tk.add_template_directory(config, 'templates/front_page')
        tk.add_template_directory(config, 'templates/theme')

    # ITemplateHelpers
    def get_helpers(self):
        return {'simple_frontpage_datasets_list': _datasets_list}

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
