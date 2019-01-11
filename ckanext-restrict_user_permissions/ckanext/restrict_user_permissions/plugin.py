import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

# This function prohibits a normal user to access user settings (change password, etc.).
# Only sysadmins will be able to do so.
# This also deactivates and hides the "Manage" button inside the user's profile page.
def user_update(context, data_dict=None):
    return {'success': False, 'msg': 'You are not authorized to update the user profile'}


class Restrict_User_PermissionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'restrict_user_permissions')

    def get_auth_functions(self):
        return {'user_update': user_update}