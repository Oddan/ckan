import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import model
from ckan.model import meta, Session
from ckan.model import types as _types
from sqlalchemy import types, Table, Column, ForeignKey, orm


import pdb

TITLE_MAX_LENGTH = 100


reference_dataset_table = None
dataset_component_table = None
data_format_table = None
organization_additional_info_table = None
person_table = None

class Person(model.domain_object.DomainObject):
    pass

class OrganizationAdditionalInfo(model.domain_object.DomainObject):
    pass

def setup_model():
    #pdb.set_trace()

    #prepare_reference_dataset_table()
    #prepare_dataset_component_table()
    prepare_data_format_table()
    prepare_person_table()
    prepare_organization_table()


def prepare_person_table():

    global person_table
    if person_table is None:
        person_table = Table(
            'person', meta.metadata,
            Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
            Column('first_name', types.UnicodeText, nullable=False),
            Column('last_name', types.UnicodeText, nullable=False),
            Column('email', types.UnicodeText),
            Column('affiliation_id', types.UnicodeText, ForeignKey('group.id'))
        )

    meta.mapper(Person, person_table,
                properties={'affiliation': orm.relation(model.group.Group,
                                                        backref=orm.backref('affiliates'))}
    )

    ensure_table_created(person_table)


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


class CdsmetadataPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)

    # =============================== IConfigurable ===========================

    def configure(self, config):
        setup_model()

    # ================================ IConfigurer ============================

    
    



    def update_config(self, config_):
        # pdb.set_trace()
        toolkit.add_template_directory(config_, 'templates')

        
        
        
        # toolkit.add_public_directory(config_, 'public')
        # toolkit.add_resource('fanstatic', 'cdsmetadata')
