from ckan.common import config

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

def group_create(context, data_dict=None):
    
    # Get the user name of the logged-in user
    user_name = context['user']

    # Get a list of the members of the 'curators' group
    try:
        members = toolkit.get_action('member_list')(
            data_dict={'id': 'curators', 'object_type': 'user'})
    except toolkit.ObjectNotFound:
        # the curators group doesn't exist
        return {'success': False,
                'msg': "The curators group doesn't exist, so only sysadmins "
                "are authorized to create groups."}
                

    # 'members' is a list of (user_id, object_type, capacity) tuples, we're
    # only interested in the user_ids.
    member_ids = [member_tuple[0] for member_tuple in members]

    # We have the logged-in user's user name, get their user id
    convert_user_name_or_id_to_id = toolkit.get_converter(
        'convert_user_name_or_id_to_id')
    try:
        user_id = convert_user_name_or_id_to_id(user_name, context)
    except toolkit.Invalid:
        # The user doesn't exist (e.g. they're not logged-in)
        return {'success': False,
                'msg': 'You must be logged-in as a member of the curators '
                ' group to create new groups.'}
    

    # Finally, we can test whether the user is a member of the curators group
    if user_id in member_ids:
        return {'success': True}
    else:
        return {'success': False,
                'msg': 'Only curators are allowed to create groups.'}

def group_create2(context, data_dict=None):

    # Get the value of the ckan.iauthfunctions.users_can_create_groups
    # setting from the CKAN config file as a string, or False if the setting
    # isn't in the config file.

    users_can_create_groups = config.get(
        'ckan.iauthfunctions.users_can_create_groups', False)

    # Convert the value from a string to a boolean
    users_can_create_groups = toolkit.asbool(users_can_create_groups)

    if users_can_create_groups:
        return {'success': True}
    else:
        return {'success': False,
                'msg': 'Only sysadmins can create groups'}

    
class ExampleIAuthFunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self):
        return {'group_create': group_create2}



# class IauthfunctionsPlugin(plugins.SingletonPlugin):
#     plugins.implements(plugins.IConfigurer)

#     # IConfigurer

#     def update_config(self, config_):
#         toolkit.add_template_directory(config_, 'templates')
#         toolkit.add_public_directory(config_, 'public')
#         toolkit.add_resource('fanstatic', 'iauthfunctions')
