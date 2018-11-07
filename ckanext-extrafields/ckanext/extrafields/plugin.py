import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ipdb

def create_country_codes():
    #ipdb.set_trace(context=5)
    print('entered create_country_codes')
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    try:
        data = {'id': 'country_codes'}
        tk.get_action('vocabulary_show')(context, data)
    except tk.ObjectNotFound:
        data = {'name': 'country_codes'}
        vocab = tk.get_action('vocabulary_create')(context, data)
        for tag in (u'uk', u'ie', u'de', u'fr', u'es'):
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            tk.get_action('tag_create')(context, data)

def country_codes():
    #ipdb.set_trace()
    create_country_codes()
    try:
        tag_list = tk.get_action('tag_list')
        country_codes = tag_list(data_dict={'vocabulary_id': 'country_codes'})
        return country_codes
    except tk.ObjectNotFound:
        return None

class ExampleIDatasetFormPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IDatasetForm)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)

    def get_helpers(self):
        return {'country_codes': country_codes}

    def _modify_package_schema(self, schema):
        create_country_codes()
        schema.update({
            'country_code' : [
                tk.get_validator('ignore_missing'),
                tk.get_converter('convert_to_tags')('country_codes')
            ]
        })
        schema.update({
            'custom_text' : [
                tk.get_validator('ignore_missing'),
                tk.get_converter('convert_to_extras')
            ]
        })
        # add our custom_resource_text metadata field to the schema
        schema['resources'].update({
            'custom_resource_text' : [tk.get_validator('ignore_missing') ]
            })

        return schema
    
    def create_package_schema(self):
        print('create')
        schema = super(ExampleIDatasetFormPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        print('update')
        schema = super(ExampleIDatasetFormPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        print('show_package_schema')
        schema = super(ExampleIDatasetFormPlugin, self).show_package_schema()
        schema['tags']['__extras'].append(tk.get_converter('free_tags_only'))
        schema.update({
            'country_code': [
                tk.get_converter('convert_from_tags')('country_codes'),
                tk.get_validator('ignore_missing')]
            })
        schema.update({
            'custom_text' : [tk.get_converter('convert_from_extras'),
                             tk.get_validator('ignore_missing')]})

        schema['resources'].update({
            'custom_resource_text' : [tk.get_validator('ignore_missing') ]
            })
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for package
        # types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above)
        return []

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        tk.add_template_directory(config, 'templates')
    

# class ExtrafieldsPlugin(plugins.SingletonPlugin):
#     plugins.implements(plugins.IConfigurer)

#     # IConfigurer

#     def update_config(self, config_):
#         toolkit.add_template_directory(config_, 'templates')
#         toolkit.add_public_directory(config_, 'public')
#         toolkit.add_resource('fanstatic', 'extrafields')
