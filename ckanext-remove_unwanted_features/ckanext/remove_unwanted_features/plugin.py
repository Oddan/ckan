import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

# If this function is used, it prohibits a normal user to access user settings (change password, etc.).
# Only sysadmins will be able to do so.
# This also deactivates and hides the "Manage" button inside the user's profile page.
def user_update(context, data_dict=None):
    return {'success': False, 'msg': 'You are not authorized to update the user profile'}

# If this function is used, it allows users to delete their own profiles
def user_delete(context, data_dict=None):
    return {'success': True, 'msg':''}


class Remove_Unwanted_FeaturesPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'remove_unwanted_features')


    # IAuthFunctions

    def get_auth_functions(self):
        return {'user_delete': user_delete} #Dictionary containing which of the custom functions defined above to use