import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan import model
from ckan.model import meta, Session
from ckan.model.types import make_uuid
from ckan.common import request, g, _
from sqlalchemy import types, Table, Column, ForeignKey, orm
from sqlalchemy.types import UnicodeText, Unicode, Boolean
import ckan.logic as logic
import ckan.logic.schema as _schema
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.base import abort, render

import pdb

project_types = ['Pilot', 'Commercial', 'Other']


def project_type_validator(value, context):
    if value not in project_types:
        raise Invalid(_('Unknown project type.'))
    return value


def allow_empty_user(value, context):
    if not value:
        return value  # allow empty values
    return tk.get_validator('user_id_or_name_exists')(value, context)

class DatasetMetadataPlugin(plugins.SingletonPlugin,
                            tk.DefaultDatasetForm):
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IPackageController, inherit=True)

    # ============================ IPackageController =========================
    def after_create(self, context, pkg_dict):
        #pdb.set_trace()
        pass
    
    

    # ============================= ITemplateHelpers ==========================
    def get_helpers(self):
        return {'project_types': lambda: [{'value': x} for x in project_types]}

    # ================================ IValidators ============================
    def get_validators(self):
        return {'project_type_validator': project_type_validator,
                'user_id_or_name_exists_allow_empty': allow_empty_user}


    # ================================ IConfigurer ============================

    def update_config(self, config_):

        tk.add_template_directory(config_, 'templates')

    # =============================== IDatasetForm ============================

    def is_fallback(self):
        return True

    def _modify_package_schema(self, schema):
        schema.update({
            'contact_person': [tk.get_validator('ignore_missing'),
                               tk.get_validator('user_id_or_name_exists_allow_empty'),
                               tk.get_converter('convert_to_extras')],
            'project_type': [tk.get_validator('project_type_validator'),
                             tk.get_converter('convert_to_extras')],
            'start_date_covered': [tk.get_validator('isodate'),
                                   tk.get_converter('convert_to_extras')],
            'end_date_covered': [tk.get_validator('isodate'),
                                 tk.get_converter('convert_to_extras')]
        })
        return schema

    def package_types(self):
        return []

    def create_package_schema(self):
        schema = super(DatasetMetadataPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(DatasetMetadataPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(DatasetMetadataPlugin, self).show_package_schema()
        schema.update({
            'contact_person': [tk.get_converter('convert_from_extras'),
                               tk.get_validator('ignore_missing'),
                               tk.get_validator('user_id_or_name_exists_allow_empty')],
            'project_type': [tk.get_converter('convert_from_extras'),
                             tk.get_validator('project_type_validator')],
            'start_date_covered': [tk.get_converter('convert_from_extras'),
                                   tk.get_validator('isodate')],
            'end_date_covered': [tk.get_converter('convert_from_extras'),
                                 tk.get_validator('isodate')]
        })
        return schema
