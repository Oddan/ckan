import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


def my_datasets_list():
    # returns a list of max 5 datasets (packages).

    datasets = toolkit.get_action('current_package_list_with_resources')(data_dict={'limit':5})

    return datasets



class Simple_FrontpagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'simple_frontpage')

    def get_helpers(self):
        # register the datasets_list function defined above as a template helper
        return {'simple_frontpage_datasets_list': my_datasets_list}