import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


# This function sets the authorisation to download a dataset
def user_download_dataset(context, data_dict=None):
    return {'success': False, 'msg': 'You are not authorized to download the dataset.'}


class Datasets_Landing_PagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_public_directory(config_, '../../../ckan/public/test_dataset_public_files')
        toolkit.add_resource('fanstatic', 'datasets_landing_page')


    # IAuthFunctions

    def get_auth_functions(self):
        return {'user_download_dataset': user_download_dataset}