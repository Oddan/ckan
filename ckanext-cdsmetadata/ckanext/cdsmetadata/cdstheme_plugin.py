import ckan.plugins as plugins
import ckan.plugins.toolkit as tk


def _datasets_list():
    return tk.get_action('current_package_list_with_resources')(
        data_dict={'limit': 5}
    )


class CdsThemePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer
    def update_config(self, config):
        tk.add_public_directory(config, 'public')
        tk.add_template_directory(config, 'templates/front_page')
        tk.add_template_directory(config, 'templates/theme')

    # ITemplateHelpers
    def get_helpers(self):
        return {'simple_frontpage_datasets_list': _datasets_list}
