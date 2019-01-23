import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import pdb

@toolkit.auth_allow_anonymous_access
def deny(context, data_dict=None):
    return {'success': False,
            'msg': 'Nobody should have access yet.'}

@toolkit.auth_allow_anonymous_access
def accept(context, data_dict=None):
    return {'success': True}


class CDSCAccessManagementPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self):
        return {'resource_create': deny,
                'resource_delete': deny,
                'resource_show'  : deny,
                'resource_update': deny,
                'resource_view_list': accept}
    
