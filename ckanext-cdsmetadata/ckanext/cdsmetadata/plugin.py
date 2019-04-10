import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from ckan import model
from ckan.model import meta, Session
from ckan.model import types as _types
from ckan.common import request, g, _, json
from sqlalchemy import types, Table, Column, ForeignKey, orm
import ckan.logic as logic
import ckan.logic.schema as _schema
from six import text_type
from ckan.views import api
from ckan.lib.navl.dictization_functions import Invalid

import pdb

TITLE_MAX_LENGTH = 100


reference_dataset_table = None
dataset_component_table = None
data_format_table = None
organization_additional_info_table = None
user_extra_table = None

class UserExtra(model.domain_object.DomainObject):
    def __init__(self, first_name, last_name, user_id):
        self.first_name = first_name
        self.last_name = last_name
        self.user_id = user_id

class OrganizationAdditionalInfo(model.domain_object.DomainObject):
    pass

def setup_model():
    #pdb.set_trace()

    #prepare_reference_dataset_table()
    #prepare_dataset_component_table()
    #prepare_data_format_table()
    prepare_user_extra_table()
    #prepare_organization_table()


def prepare_user_extra_table():

    global user_extra_table
    if user_extra_table is None:
        user_extra_table = Table(
            'user_extra', meta.metadata,
            Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
            Column('first_name', types.UnicodeText, nullable=False),
            Column('last_name', types.UnicodeText, nullable=False),
            Column('user_id', types.UnicodeText, ForeignKey('user.id'))
        )

        meta.mapper(UserExtra, user_extra_table,
                    properties={'user': orm.relation(model.user.User,
                                                     backref=orm.backref('extra',
                                                            uselist=False,
                                                            cascade='all, delete, delete-orphan'))}
    )

    ensure_table_created(user_extra_table)

def prepare_organization_table():

    global organization_additional_info_table

    if organization_additional_info_table is None:
        organization_additional_info_table = Table(
            'organization_additional_info', meta.metadata,
            Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
            Column('group_id', types.UnicodeText, ForeignKey('group.id')),
            Column('homepage', types.UnicodeText),
            Column('contact_id', types.UnicodeText, ForeignKey('person.id'))
        )

        meta.mapper(
            OrganizationAdditionalInfo, organization_additional_info_table,
            properties = {'contact' : orm.relation(Person,
                                            backref=orm.backref('spokesperson')),
                          'group' : orm.relation(model.group.Group,
                                            backref=orm.backref('extras',
                                                uselist=False,
                                                cascade='all, delete, delete-orphan'))}
    )

    ensure_table_created(organization_additional_info_table)
        
def prepare_data_format_table():

    global data_format_table

    if data_format_table is None:
        data_format_table = Table(
            'data_format', meta.metadata,
            Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
            Column('name', types.Unicode(TITLE_MAX_LENGTH), nullable=False, unique=True),
            Column('is_open', types.Boolean),
            Column('description', types.UnicodeText)
        )

    # create table
    ensure_table_created(data_format_table)


def prepare_reference_dataset_table():

    # setup table
    global reference_dataset_table

    # reference_dataset_table = Table(
    #     'reference_dataset', meta.metadata,
    #     Column('dill', types.UnicodeText, primary_key=True),
    #     Column(...)
    # )

    # create table
    #ensure_table_created(reference_dataset_table)


def ensure_table_created(table):
    if not table.exists():
        try:
            table.create()
        except Exception, e:
            # remove possibly incorrectly created table
            Session.execute('DROP TABLE ' + table.fullname)



def _user_modif_wrapper(action_name):

    action = toolkit.get_action(action_name)

    def _wrapper(context, data_dict):

        first_name = data_dict.get('first_name', '')
        last_name = data_dict.get('last_name', '')
        
        # sync 'fullname' with 'first_name' and last_name'
        if 'fullname' not in data_dict.keys():
            data_dict['fullname'] = '{0} {1}'.format(first_name, last_name)

        result_dict = action(context, data_dict)

        result_dict['first_name'] = first_name
        result_dict['last_name'] = last_name
        
        # updating the extra information (not found in the original user object)
        
        new_extra = model.User.get(result_dict['id']).extra
        if new_extra is None:
            new_extra = UserExtra(first_name, last_name, result_dict['id'])
        else:
            new_extra.first_name = first_name
            new_extra.last_name = last_name
        new_extra.save()

        return result_dict

    return _wrapper
        
def _user_show_wrapper():
    
    action = toolkit.get_action('user_show')

    def _wrapper(context, data_dict):

        result_dict = action(context, data_dict)
        extra = model.User.get(result_dict['id']).extra
        if extra is not None:
            result_dict['first_name'] = extra.first_name
            result_dict['last_name'] = extra.last_name

        return result_dict

    return _wrapper

def _username_helper_fun(user, maxlength=0):
    if not isinstance(user, model.User):
        user_name = text_type(user)
        result = user_name
        user = model.User.get(user_name)
        if user:
            result = user.name
    else:
        result = user.name
    
    if maxlength and len(result) > maxlength:
        result = result[:maxlength] + '...'
    
    return result

def autocomplete_filtered():

    q = request.args.get(u'q', u'')
    org_id = request.args.get(u'org_id', u'')
    limit = request.args.get(u'limit', 20)
    user_list = []
    if q:
        context = {u'model': model, u'session': model.Session,
                   u'user': g.user, u'auth_user_obj': g.userobj}

        data_dict = {u'q': q, u'limit': limit}

        # get list with matching user names
        user_list = toolkit.get_action(u'user_autocomplete')(context, data_dict)

        # narrow down to list of users who are actual members
        if org_id:
            member_list = toolkit.get_action('member_list')(
                {'model' : model}, {'id' : org_id})
            member_ids = [x[0] for x in member_list]
            user_list = [u for u in user_list if u['id'] in member_ids]

    return api._finish_ok(user_list)

def contact_person_validator(value, context):

    org_id = context['group'].id
    member_list = toolkit.get_action('member_list') (
        {'model' : model}, {'id' : org_id})
    member_ids = [x[0] for x in member_list]

    user = model.User.by_name(value)
    if user is None:
        raise Invalid(_('Unknown user entered as contact person.'))

    if not user.id in member_ids:
        raise Invalid(_('Specified user is not member of the organization.'))

    return value


class CdsmetadataPlugin(plugins.SingletonPlugin, toolkit.DefaultOrganizationForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IGroupForm)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IValidators)

    # ================================ IValidators ============================
    def get_validators(self):

        return {'valid_contact_person' : contact_person_validator}
         
    
    # ============================= ITemplateHelpers ==========================
    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        blueprint.add_url_rule('/api/co2datashare/autocomplete_filtered',
                               view_func=autocomplete_filtered)
        return blueprint
    
    # ============================= ITemplateHelpers ==========================
    def get_helpers(self):
        return {'username' : _username_helper_fun}
    
    # ================================= IActions ==============================
    def get_actions(self):

        result = {}
        for aname in ['user_create', 'user_update']:
            result[aname] = _user_modif_wrapper(aname)

        result['user_show'] = _user_show_wrapper()
            
        return result;

    # =============================== IConfigurable ===========================

    def configure(self, config):
        setup_model()
        #pdb.set_trace()

    # ================================ IConfigurer ============================

    def update_config(self, config_):
        # pdb.set_trace()
        toolkit.add_template_directory(config_, 'templates')

        # toolkit.add_public_directory(config_, 'public')
        # toolkit.add_resource('fanstatic', 'cdsmetadata')

    # ================================ IGroupForm =============================
    is_organization = True
    
    def is_fallback(self):
        #pdb.set_trace()
        return True

    def group_types(self):
        #pdb.set_trace()
        return []

    def group_controller(self):
        #pdb.set_trace()
        pass

    def form_to_db_schema(self):
        #pdb.set_trace()
        schema = super(CdsmetadataPlugin, self).form_to_db_schema()
        schema.update({'homepageURL': [toolkit.get_validator('ignore_missing'),
                                        toolkit.get_converter('convert_to_extras')]})
        schema.update({'contact_person':
                       [toolkit.get_validator('ignore_missing'),
                        toolkit.get_validator('valid_contact_person'),
                        toolkit.get_converter('convert_to_extras')]})

        return schema
        
    def db_to_form_schema(self):
        schema=self._default_show_group_schema()

        schema.update({'homepageURL' : [toolkit.get_converter('convert_from_extras'),
                                        toolkit.get_validator('ignore_missing')]})
        schema.update({'contact_person':[toolkit.get_converter('convert_from_extras'),
                                         toolkit.get_validator('ignore_missing')]})
        return schema

    def _default_show_group_schema(self):
        schema = _schema.default_group_schema()

        # make default show schema behave like when run with no validation
        schema['num_followers'] = []
        schema['created'] = []
        schema['display_name'] = []
        #schema['extras'] = {'__extras': [keep_extras]}  # has to be removed, or extras won't work
        schema['package_count'] = [toolkit.get_validator('ignore_missing')]
        schema['packages'] = {'__extras': [toolkit.get_validator('keep_extras')]}
        schema['revision_id'] = []
        schema['state'] = []
        schema['users'] = {'__extras': [toolkit.get_validator('keep_extras')]}
        
        return schema
        
    
    # def check_data_dict(self, data_dict):
    #     pdb.set_trace()
    #     pass

    # def new_template(self):
    #     pass

    # def index_template(self):
    #     pass

    # def read_template(self):
    #     pass
    
    # def history_template(self):
    #     pass
    
    # def edit_template(self):
    #     pass
        
    # def group_form(self):
    #     pass
    
    # def setup_template_variables(self, context, data_dict):
    #     pass
    
    # def validate(self, context, data_dict, schema, action):
    #     pass
