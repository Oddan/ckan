import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from flask import Blueprint
from ckan import model
from ckan.model import meta, Session
from ckan.model.types import make_uuid
from ckan.common import request, g, _
from sqlalchemy import types, Table, Column, ForeignKey, orm, or_
from sqlalchemy.types import UnicodeText, Unicode, Boolean
import ckan.logic as logic
import ckan.logic.schema as _schema
from ckan.logic import ValidationError
from six import text_type
from ckan.views import api
from ckan.lib.navl.dictization_functions import Invalid, Missing
from ckan.lib.base import abort, render
from resource_category import ResourceCategory, ResourceCategoryMetadataItem, category_metadata_datatypes
from ckan.lib import helpers as h
from plugin2 import get_required_metadata_fields
import re


import copy, datetime, dateutil
import pdb

TITLE_MAX_L = 100
NAME_MAX_L = 100
EMAIL_MAX_L = 500

data_format_table = None
license_table = None
publication_table = None
person_table = None
organization_extra_table = None


affiliation_association_table = None  # associate Person with Organization
contact_org_association_table = None  # associate contact Person with Organization
contact_dataset_association_table = None # associate contact with Dataset
person_contributor_dataset_association_table = None # contributor (Person) with dataset
org_contributor_dataset_association_table = None # contributor (Organization) with dataset
dataset_publication_association_table = None # Associate publications with datasets
dataset_dataset_association_table = None # Associate related datasets


class Person(model.domain_object.DomainObject):
    def __init__(self, first_name, last_name, email):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

    @property
    def name(self):
        return self.last_name + ", " + self.first_name


class OrganizationExtra(model.domain_object.DomainObject):
    def __init__(self, homepageURL, org_id):
        self.homepageURL = homepageURL
        self.org_id = org_id


class DataFormat(model.domain_object.DomainObject):
    def __init__(self, name, is_open, description):
        self.name = name
        self.is_open = is_open
        self.description = description

    @property
    def resources(self):
        # @@ inefficient implementation.  Is there a way to do this directly
        # using sqlalchemy?
        result = filter(lambda r: r.extras.get('dataformat', None) == self.id,
                      Session.query(model.Resource).all())

        return sorted(result, key=lambda x: x.name)


class License(model.domain_object.DomainObject):
    def __init__(self, name, description, license_url):
        self.name = name
        self.description = description
        self.license_url = license_url


class Publication(model.domain_object.DomainObject):
    def __init__(self, name, citation, doi):
        self.name = name
        self.citation = citation
        self.doi = doi


def setup_model():

    # object tables
    prepare_data_format_table()
    prepare_organization_extra_table()
    prepare_license_table()
    prepare_publication_table()
    prepare_person_table()

    # association tables
    prepare_affiliation_association_table()
    prepare_contact_org_association_table()
    prepare_contact_dataset_association_table()
    prepare_person_contributor_dataset_association_table()
    prepare_org_contributor_dataset_association_table()
    prepare_dataset_publication_association_table()
    prepare_dataset_dataset_association_table()


def prepare_dataset_dataset_association_table():

    global dataset_dataset_association_table

    if dataset_dataset_association_table is None:
        dataset_dataset_association_table = Table(
            'dataset_dataset_association', meta.metadata,
            Column('id', UnicodeText, primary_key=True, default=make_uuid),
            Column('dset1_id', UnicodeText, ForeignKey('package.id')),
            Column('dset2_id', UnicodeText, ForeignKey('package.id'))
        )

        # create table
        ensure_table_created(dataset_dataset_association_table)

        class DatasetAssociator(model.domain_object.DomainObject):
            def __init__(self, dset1_id, dset2_id):
                self.dset1_id = dset1_id
                self.dset2_id = dset2_id

        meta.mapper(DatasetAssociator, dataset_dataset_association_table)

        # since we cannot run meta.mapper on Package again, we will have to add
        # our own implementation of a relationship property

        def remove_links(id):
            entries = \
                meta.Session.query(DatasetAssociator).filter(
                    (DatasetAssociator.dset1_id == id) |
                    (DatasetAssociator.dset2_id == id))

            for e in entries:
                meta.Session.delete(e)

            meta.Session.commit()

        def getter(self):
            entries = \
                meta.Session.query(DatasetAssociator).\
                filter_by(dset1_id=self.id)

            result = [meta.Session.query(model.package.Package).get(x.dset2_id)
                      for x in entries]
            return result

        def setter(self, other_datasets):

            remove_links(self.id)

            other_datasets = _ensure_list(other_datasets)

            for other in other_datasets:
                if other.id == self.id:
                    # ignore self-references
                    continue
                meta.Session.add(DatasetAssociator(self.id, other.id))
                meta.Session.add(DatasetAssociator(other.id, self.id))

            meta.Session.commit()  # @@ could it cause trouble to commit here?

        model.package.Package.related_dataset = property(fget=getter,
                                                         fset=setter)


def prepare_dataset_publication_association_table():

    global dataset_publication_association_table

    if dataset_publication_association_table is None:
        dataset_publication_association_table = Table(
            'dataset_publication_association', meta.metadata,
            Column('dataset_id', UnicodeText, ForeignKey('package.id')),
            Column('pub_id', UnicodeText, ForeignKey('publication.id'))
        )

        # create table
        ensure_table_created(dataset_publication_association_table)


def prepare_org_contributor_dataset_association_table():

    global org_contributor_dataset_association_table

    if org_contributor_dataset_association_table is None:
        org_contributor_dataset_association_table = Table(
            'org_contributor_dataset_association', meta.metadata,
            Column('dataset_id', UnicodeText, ForeignKey('package.id')),
            Column('org_id', UnicodeText, ForeignKey('organization_extra.id'))
        )

        # create table
        ensure_table_created(org_contributor_dataset_association_table)


def prepare_person_contributor_dataset_association_table():

    global person_contributor_dataset_association_table

    if person_contributor_dataset_association_table is None:
        person_contributor_dataset_association_table = Table(
            'person_contributor_dataset_association', meta.metadata,
            Column('dataset_id', UnicodeText, ForeignKey('package.id')),
            Column('person_id', UnicodeText, ForeignKey('person.id'))
        )

        # create table
        ensure_table_created(person_contributor_dataset_association_table)


def prepare_contact_dataset_association_table():

    global contact_dataset_association_table
    if contact_dataset_association_table is None:
        contact_dataset_association_table = Table(
            'contact_dataset_association', meta.metadata,
            Column('dataset_id', UnicodeText, ForeignKey('package.id')),
            Column('person_id', UnicodeText, ForeignKey('person.id'))
        )

        # create table
        ensure_table_created(contact_dataset_association_table)


def prepare_contact_org_association_table():

    global contact_org_association_table
    if contact_org_association_table is None:
        contact_org_association_table = Table(
            'contact_org_association', meta.metadata,
            Column('org_id', UnicodeText, ForeignKey('group.id')),
            Column('person_id', UnicodeText, ForeignKey('person.id')),
        )

        # create table
        ensure_table_created(contact_org_association_table)


def prepare_affiliation_association_table():

    global affiliation_association_table
    if affiliation_association_table is None:
        affiliation_association_table = Table(
            'affiliation_association', meta.metadata,
            Column('org_id', UnicodeText, ForeignKey('group.id')),
            Column('person_id', UnicodeText, ForeignKey('person.id')),
        )

        # create table
        ensure_table_created(affiliation_association_table)


def prepare_person_table():

    global person_table

    if person_table is None:
        person_table = Table(
            'person', meta.metadata,
            Column('id', UnicodeText, primary_key=True, default=make_uuid),
            Column('first_name', Unicode(NAME_MAX_L)),
            Column('last_name', Unicode(NAME_MAX_L), nullable=False),
            Column('email',  Unicode(EMAIL_MAX_L))
        )
        meta.mapper(
            Person, person_table,
            properties={'affiliation':
                        orm.relationship(
                            model.group.Group,
                            secondary=lambda: affiliation_association_table,
                            backref=orm.backref(
                                'people',
                                cascade='save-update, merge')),
                        'contact_org':
                        orm.relationship(
                            model.group.Group,
                            secondary=lambda: contact_org_association_table,
                            backref=orm.backref(
                                'contact_person',
                                cascade='save-update, merge')),
                        'contact_dataset':
                        orm.relationship(
                            model.package.Package,
                            secondary=lambda: contact_dataset_association_table,
                            backref=orm.backref(
                                'contact_person',
                                cascade='save-update, merge')),
                        'contributor_dataset':
                        orm.relationship(
                            model.package.Package,
                            secondary=lambda : person_contributor_dataset_association_table,
                            backref=orm.backref(
                                'person_contributor',
                                cascade='save-update, merge'))})

        # create table
        ensure_table_created(person_table)


def prepare_publication_table():

    global publication_table

    if publication_table is None:
        publication_table = Table(
            'publication', meta.metadata,
            Column('id', UnicodeText, primary_key=True, default=make_uuid),
            Column('name', Unicode(TITLE_MAX_L), nullable=False, unique=True),
            Column('citation', UnicodeText),
            Column('doi', Unicode(TITLE_MAX_L), unique=True)
        )
        meta.mapper(
            Publication, publication_table,
            properties={'datasets':
                        orm.relationship(
                            model.package.Package,
                            secondary=lambda: dataset_publication_association_table,
                            backref=orm.backref(
                                'publications',
                                cascade='save-update, merge'))})

        # create table
        ensure_table_created(publication_table)


def prepare_license_table():

    global license_table

    if license_table is None:
        license_table = Table(
            'license', meta.metadata,
            Column('id', UnicodeText, primary_key=True, default=make_uuid),
            Column('name', Unicode(TITLE_MAX_L), nullable=False, unique=True),
            Column('description', UnicodeText),
            Column('license_url', UnicodeText)
        )

        meta.mapper(License, license_table)

    # create table
    ensure_table_created(license_table)


def prepare_data_format_table():

    global data_format_table

    if data_format_table is None:
        data_format_table = Table(
            'data_format', meta.metadata,
            Column('id', UnicodeText, primary_key=True, default=make_uuid),
            Column('name', Unicode(TITLE_MAX_L), nullable=False, unique=True),
            Column('is_open', Boolean),
            Column('description', UnicodeText)
        )

        meta.mapper(DataFormat, data_format_table)

    # create table
    ensure_table_created(data_format_table)


def prepare_organization_extra_table():

    global organization_extra_table
    if organization_extra_table is None:
        organization_extra_table = Table(
            'organization_extra', meta.metadata,
            Column('id', UnicodeText, primary_key=True, default=make_uuid),
            Column('homepageURL', UnicodeText),
            Column('org_id', UnicodeText, ForeignKey('group.id'))
        )

        meta.mapper(OrganizationExtra, organization_extra_table,
                    properties={'organization':
                                orm.relation(model.group.Group,
                                             backref=orm.backref(
                                                 'extra',
                                                 uselist=False,
                                                 cascade='all, delete, delete-orphan')),
                                'datasets_contributed_to':
                                orm.relationship(
                                    model.package.Package,
                                    secondary=lambda: org_contributor_dataset_association_table,
                                    backref=orm.backref(
                                        'org_contributor',
                                        cascade='save-update, merge'))})

        # create table
        ensure_table_created(organization_extra_table)



def ensure_table_created(table):

    # if table.exists():
    #     table.drop() # @@@@
    #     Session.commit()

    if not table.exists():
        try:
            table.create()
        except Exception as e:
            # remove possibly incorrectly created table
            Session.rollback()
            # Session.execute('DROP TABLE ' + table.fullname)
            # Session.commit()


def _organization_modif_wrapper(action_name):

    action = tk.get_action(action_name)

    def _wrapper(context, data_dict):

        result_dict = action(context, data_dict)

        # updating the extra information

        homepageURL = data_dict.get('homepageURL', '')

        new_extra = model.Group.get(result_dict['id']).extra
        if new_extra is None:
            new_extra = OrganizationExtra(homepageURL, result_dict['id'])
            new_extra.save()  # necessary to access .organization below
        else:
            new_extra.homepageURL = homepageURL

        result_dict['homepageURL'] = homepageURL

        new_extra.organization.contact_person = \
            _list_people(context['session'],
                         data_dict.get('contact_person', []))
        new_extra.organization.people = \
            _list_people(context['session'],
                         data_dict.get('people', []))

        new_extra.datasets_contributed_to = \
            _list_datasets(context['session'],
                           data_dict.get('dataset_contributions', []))

        new_extra.save()

        return result_dict

    return _wrapper


def _organization_show_wrapper():

    action = tk.get_action('organization_show')

    def _wrapper(context, data_dict):
        result_dict = action(context, data_dict)

        # recovering extra information
        new_extra = model.Group.get(result_dict['id']).extra

        homepageURL = '' if new_extra is None else new_extra.homepageURL
        result_dict['homepageURL'] = homepageURL

        # recovering contact people, if any
        id = data_dict.get('id', None)
        org = model.Group.get(id)
        result_dict['contact_person'] = \
            [(x.id, x.name, x.email) for x in org.contact_person]
        result_dict['people'] = \
            [(x.id, x.name, x.email) for x in org.people]

        if new_extra is not None:

            result_dict['datasets_contributed_to'] = \
                [[x.id, x.title, x.owner_org]
                 for x in new_extra.datasets_contributed_to]
            for li in result_dict['datasets_contributed_to']:
                owner_org = model.Group.get(li[2])
                li[2] = "" if owner_org is None else owner_org.title

        if result_dict['contact_person'] is not None:
            result_dict['contact_person'].sort(key=lambda x: x[1])

        if result_dict['people'] is not None:
            result_dict['people'].sort(key=lambda x: x[1])

        return result_dict

    return _wrapper


def _edit_metadata_auth(context, data_dict=None):
    user_name = context.get('user', None)
    if user_name is None:
        return {'success': False, 'msg': 'User not logged in.'}

    # at the moment, only sysadmins should have access to metadata editing, and
    # sysadmins would bypass the authorization system anyway, so there is no
    # way this function needs to return anything other than False.
    return {'success': False, 'msg': 'Only sysadmins can edit metadata'}


def check_edit_metadata():

    try:
        context = {'model': model, 'user': g.user,
                   'auth_user_obj': g.userobj}
        tk.check_access('edit_metadata', context)
    except logic.NotAuthorized:
        abort(403, _('Not authorized to see this page.'))


def _ensure_list(obj):
    return \
        obj if isinstance(obj, list) else \
        [] if obj is None else \
        [obj]


def _list_people(session, people_ids):

    people_ids = _ensure_list(people_ids)
    people_query = session.query(Person)
    result = []
    for id in people_ids:
        person = people_query.get(id)
        if person:
            result.append(person)

    return result


def _list_orgs(session, org_ids):
    org_ids = _ensure_list(org_ids)
    org_query = session.query(model.group.Group)
    result = []
    for id in org_ids:
        org = org_query.get(id)
        if org:
            result.append(org)
    return result


def _list_pubs(session, pub_ids):
    pub_ids = _ensure_list(pub_ids)
    pub_query = session.query(Publication)
    result = []
    for id in pub_ids:
        pub = pub_query.get(id)
        if pub:
            result.append(pub)

    return result


def _list_datasets(session, dset_ids):
    dset_ids = _ensure_list(dset_ids)
    dset_query = session.query(model.package.Package)
    result = []
    for id in dset_ids:
        dset = dset_query.get(id)
        if dset:
            result.append(dset)
    return result


def _person_create(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)

    new_person = Person(data_dict['first_name'],
                        data_dict['last_name'],
                        data_dict['email'])
    new_person.affiliation = \
        _list_orgs(context['session'], data_dict['affiliation'])
    new_person.contact_org = \
        _list_orgs(context['session'], data_dict['contact_org'])
    new_person.contact_dataset = \
        _list_datasets(context['session'], data_dict['contact_dataset'])
    new_person.contributor_dataset = \
        _list_datasets(context['session'], data_dict['contributor_dataset'])

    try:
        new_person.save()
        context['session'].commit()
    except:
        context['session'].rollback()


def _license_create(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)

    new_license = License(data_dict['name'],
                          data_dict['description'],
                          data_dict['license_url'])
    try:
        new_license.save()
        context['session'].commit()
    except:
        context['session'].rollback()


def _publication_create(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)

    new_publication = Publication(data_dict['name'],
                                  data_dict['citation'],
                                  data_dict['doi'])
    try:
        new_publication.save()
        context['session'].commit()
    except:
        context['session'].rollback()


def _data_format_create(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)

    new_dataformat = DataFormat(data_dict['name'],
                                data_dict['is_open'],
                                data_dict['description'])
    try:
        new_dataformat.save()
        context['session'].commit()
    except:
        # @@ should we issue a warning
        context['session'].rollback()


def _person_update(context, data_dict):

    tk.check_access('edit_metadata', context, data_dict)
    per = context['session'].query(Person).get(data_dict['id'])
    if per is None:
        raise tk.ObjectNotFound

    per.first_name = data_dict['first_name']
    per.last_name = data_dict['last_name']
    per.email = data_dict['email']
    per.affiliation = _list_orgs(context['session'],
                                 data_dict['affiliation'])
    per.contact_org = _list_orgs(context['session'],
                                 data_dict['contact_org'])
    per.contact_dataset = _list_datasets(context['session'],
                                         data_dict['contact_dataset'])
    per.contributor_dataset = _list_datasets(context['session'],
                                             data_dict['contributor_dataset'])

    try:
        per.save()
        context['session'].commit()
    except:
        context['session'].rollback()


def _publication_update(context, data_dict):

    tk.check_access('edit_metadata', context, data_dict)
    pub = context['session'].query(Publication).get(data_dict['id'])
    if pub is None:
        raise tk.ObjectNotFound

    pub.name = data_dict['name']
    pub.citation = data_dict['citation']
    pub.doi = data_dict['doi']
    try:
        pub.save()
        context['session'].commit()
    except:
        context['session'].rollback()


def _license_update(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)
    lic = context['session'].query(License).get(data_dict['id'])
    if lic is None:
        raise tk.ObjectNotFound

    lic.name = data_dict['name']
    lic.description = data_dict['description']
    lic.license_url = data_dict['license_url']
    try:
        lic.save()
        context['session'].commit()
    except:
        context['session'].rollback()


def _data_format_update(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)

    df = context['session'].query(DataFormat).get(data_dict['id'])
    if df is None:
        raise tk.ObjectNotFound

    df.name = data_dict['name']
    df.is_open = data_dict['is_open']
    df.description = data_dict['description']
    try:
        df.save()
        context['session'].commit()
    except:
        # @@ should we issue a warning
        context['session'].rollback()


def _person_delete(context, data_dict):

    tk.check_access('edit_metadata', context, data_dict)
    per = context['session'].query(Person).get(data_dict['id'])
    if per is None:
        raise tk.ObjectNotFound
    try:
        per.delete()
        context['session'].commit()
    except:
        context['session'].rollback()


def _publication_delete(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)
    pub = context['session'].query(Publication).get(data_dict['id'])
    if pub is None:
        raise tk.ObjectNotFound
    try:
        pub.delete()
        context['session'].commit()
    except:
        context['session'].rollback()


def _license_delete(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)
    lic = context['session'].query(License).get(data_dict['id'])
    if lic is None:
        raise tk.ObjectNotFound
    try:
        lic.delete()
        context['session'].commit()
    except:
        context['session'].rollback()


def _data_format_delete(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)
    df = context['session'].query(DataFormat).get(data_dict['id'])
    if df is None:
        raise tk.ObjectNotFound
    # context['session'].delete(df)
    try:
        df.delete()
        context['session'].commit()
    except:
        context['session'].rollback()


def _person_show(context, data_dict):
    # tk.check_access('edit_metadata', context, data_dict)
    per = context['session'].query(Person).get(data_dict['id'])
    if per is None:
        raise tk.ObjectNotFound

    return {'first_name': per.first_name,
            'last_name': per.last_name,
            'email': per.email,
            'affiliation': [(x.id, x.title) for x in per.affiliation],
            'contact_org': [(x.id, x.title) for x in per.contact_org],
            'contact_dataset': [(x.id, x.title) for x in per.contact_dataset],
            'contributor_dataset': [(x.id, x.title)
                                    for x in per.contributor_dataset]}


def _publication_show(context, data_dict):
    # tk.check_access('edit_metadata', context, data_dict)
    pub = context['session'].query(Publication).get(data_dict['id'])
    if pub is None:
        raise tk.ObjectNotFound

    pub_datasets = pub.datasets
    datasets = [] if pub_datasets is None \
        else [(x.id, x.name) for x in pub.datasets]

    return {'name': pub.name,
            'citation': pub.citation,
            'doi': pub.doi,
            'datasets': datasets}


def _license_show(context, data_dict):
    # tk.check_access('edit_metadata', context, data_dict)
    lic = context['session'].query(License).get(data_dict['id'])
    if lic is None:
        raise tk.ObjectNotFound

    return {'id': lic.id,
            'name': lic.name,
            'description': lic.description,
            'license_url': lic.license_url}


def _data_format_show(context, data_dict):
    # tk.check_access('edit_metadata', context, data_dict)

    df = context['session'].query(DataFormat).get(data_dict['id'])
    if df is None:
        raise tk.ObjectNotFound

    return {'name': df.name,
            'is_open': df.is_open,
            'description': df.description,
            'resources': df.resources}


def _category_metadata_show(context, data_dict):

    cmd = context['session'].\
          query(ResourceCategoryMetadataItem).get(data_dict['id'])
    if cmd is None:
        raise tk.ObjectNotFound

    return {'title': cmd.title,
            'category': cmd.category,
            'datatype': cmd.datatype,
            'description': cmd.description,
            'enum_items': cmd.enum_items}


def _category_metadata_create(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)

    new_item = ResourceCategoryMetadataItem(data_dict['title'],
                                            data_dict['category'],  # @@
                                            data_dict['datatype'],
                                            data_dict['description'],
                                            data_dict['enum_items'])
    new_item.save()
    context['session'].commit()


def _category_metadata_update(context, data_dict):

    tk.check_access('edit_metadata', context, data_dict)
    item = context['session'].query(
        ResourceCategoryMetadataItem).get(data_dict['id'])
    if item is None:
        raise tk.ObjectNotFound

    item.title = data_dict['title']
    item.category_id = data_dict['category']
    item.datatype = data_dict['datatype']
    item.description = data_dict['description']
    item.enum_items = data_dict['enum_items']

    item.save()


def _category_metadata_delete(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)

    item = context['session'].query(
        ResourceCategoryMetadataItem).get(data_dict['id'])
    if item is None:
        raise tk.ObjectNotFound

    item.delete()
    context['session'].commit()


def _edit_person():
    return _edit_metadata(Person, "edit_person")


def _edit_dataformat():
    return _edit_metadata(DataFormat, "edit_dataformat")


def _edit_license():
    return _edit_metadata(License, "edit_license")


def _edit_publication():
    return _edit_metadata(Publication, "edit_publication")


def _edit_category_metadata():
    return _edit_metadata(ResourceCategoryMetadataItem,
                          "edit_category_metadata")


def _update_fun(mclass):
    return {Person: 'person_update',
            DataFormat: 'dataformat_update',
            License: 'license_update',
            Publication: 'publication_update',
            ResourceCategoryMetadataItem: 'category_metadata_update'}[mclass]


def _create_fun(mclass):
    return {Person: 'person_create',
            DataFormat: 'dataformat_create',
            License: 'license_create',
            Publication: 'publication_create',
            ResourceCategoryMetadataItem: 'category_metadata_create'}[mclass]


def _delete_fun(mclass):
    return {Person: 'person_delete',
            DataFormat: 'dataformat_delete',
            License: 'license_delete',
            Publication: 'publication_delete',
            ResourceCategoryMetadataItem: 'category_metadata_delete'}[mclass]


def _personlist(selected_ids):

    people = model.Session.query(Person).all()

    peoplelist = \
        [{'value': x.id, 'text': x.name, 'selected': False} for x in people]

    peoplelist.sort(key=lambda x: x['text'])

    # set selection
    for p in peoplelist:
        if p['value'] in selected_ids:
            p['selected'] = True

    return peoplelist


def _orglist(selected_ids):

    orgs = model.Session.query(model.group.Group).\
           filter_by(state='active').all()

    orglist = \
        [{'value': x.id, 'text': x.title, 'selected': False} for x in orgs]
    orglist.sort(key=lambda x: x['text'])

    # set selection
    for o in orglist:
        if o['value'] in selected_ids:
            o['selected'] = True

    return orglist


def _dsetlist(selected_ids, omit_ids=[]):

    datasets = model.Session.query(model.package.Package).\
               filter_by(state='active').all()
    dsetlist = \
        [{'value': x.id, 'text': x.title, 'selected': False}
         for x in datasets]
    dsetlist.sort(key=lambda x: x['text'])

    # removing items that should be omitted
    omit_ids = _ensure_list(omit_ids)
    dsetlist = filter(lambda x: x['value'] not in omit_ids, dsetlist)

    # set selection
    for d in dsetlist:
        if d['value'] in selected_ids:
            d['selected'] = True

    return dsetlist


def _publist(selected_ids):

    pubs = model.Session.query(Publication).all()

    publist = \
        [{'value': x.id, 'text': x.name, 'selected': False} for x in pubs]
    publist.sort(key=lambda x: x['text'])

    # set selection
    for p in publist:
        if p['value'] in selected_ids:
            p['selected'] = True

    return publist


def _licenselist():

    licenses = model.Session.query(License).all()

    license_list = \
        [{'value': x.id, 'text': x.name, 'selected': False} for x in licenses]
    license_list.sort(key=lambda x: x['text'])

    return license_list


def _dataformatlist():

    return [{'value': x.id, 'text': x.name, 'selected': False}
            for x in model.Session.query(DataFormat).all()]


def _get_license(id):
    try:
        lic = model.Session.query(License).get(id)
        return lic
    except:
        return None


def _datasets_with_license(license_id):

    # @@ is there a better (quicker) way to do this?
    dsets = meta.Session.query(model.package.Package).all()

    result = []
    for d in dsets:
        dset_lic_id = d.extras.get('cdslicense', None)
        if dset_lic_id and dset_lic_id == license_id:
            result.append(d)

    return result


def _category_name(category_id):

    if category_id:
        res = Session.query(ResourceCategory).get(category_id)
        if res:
            return res.title
    return _("Unknown")


def _dataformat_name(dataformat_id):

    if dataformat_id:
        res = Session.query(DataFormat).get(dataformat_id)
        if res:
            return res.name
    return _("Unknown")


def _resource_category_metadata_map():

    categories = Session.query(ResourceCategory).all()

    result_map = {}
    for c in categories:
        result_map[c.code] = sorted(c.metadata_item, key=lambda x: x.title)

    return result_map


def _extra_info(mclass, data):
    if mclass == Person:
        data = data or {}  # avoid problem with referencing NoneType below
        return {'orglist_aff':
                _orglist([x[0] for x in data.get('affiliation', [])]),
                'orglist_contact':
                _orglist([x[0] for x in data.get('contact_org', [])]),
                'dsetlist_contact':
                _dsetlist([x[0] for x in data.get('contact_dataset', [])]),
                'dsetlist_contributor':
                _dsetlist([x[0] for x in data.get('contributor_dataset', [])])}
    elif mclass == ResourceCategoryMetadataItem:
        return {'available_datatypes':
                [{'value': x, 'text': x} for x in category_metadata_datatypes],
                'current_mapping': _resource_category_metadata_map()}
    else:
        return {DataFormat: None,
                License: None,
                Publication: None,
                ResourceCategoryMetadataItem: None}[mclass]


def _show_fun(mclass):
    return {Person: 'person_show',
            DataFormat: 'dataformat_show',
            License: 'license_show',
            Publication: 'publication_show',
            ResourceCategoryMetadataItem: 'category_metadata_show'}[mclass]


def _resource_category_metadata_validator(data_dict):

    title_errors = []
    enum_errors = []

    # check that attribute title is nonzero
    if data_dict['title'] == '':
        title_errors.append("Empty attribute title not allowed.")

    # check that attribute title is unique (including inherited attributes)
    cur_cat = list(data_dict['category'])
    for i in [3, 2, 1]:
        if i != 3:  # we will check a superclass
            cur_cat[2*i] = '0'
        cur_id = "".join(cur_cat)

        matches = Session.query(ResourceCategoryMetadataItem).\
            filter_by(category_id=cur_id).\
            filter_by(title=data_dict['title']).\
            filter(ResourceCategoryMetadataItem.id != data_dict.get('id', None))

        if matches.count() > 0:
            title_errors.append("An attribute with the same name \
                                 already exists for this category")
            break

    # check that title does not contain unallowed characters
    if re.search('[^-_a-zA-Z0-9]', data_dict['title']):
        title_errors.append("Title name should only contain alphanumeric \
                            characters, underscore (_) or dash (-)")

    # check that enumerations contains at least two options (if relevant)
    if data_dict['datatype'] == 'ENUM':
        items = data_dict.get('enum_items', None)
        if items is None or len(items.split(',')) < 2:
            enum_errors.append("Enumerations need at least two items.")

    # assemble error structures and raise validation error if necessary
    errors = {}
    error_summary = {}
    if title_errors:
        errors['title'] = title_errors
        error_summary['title'] = "Error in attribute title."
    if enum_errors:
        errors['enum'] = enum_errors
        error_summary['enum'] = "error in enumeration items."

    if errors:
        raise ValidationError(errors, error_summary=error_summary)

    return data_dict


def _validation_function(mclass):
    if mclass == ResourceCategoryMetadataItem:
        return _resource_category_metadata_validator
    return None


def _extract_metadata_form_data(form, mclass):
    data_dict = {}
    for key in form.keys():
        if key == 'save':
            data_dict['id'] = form[key]
            continue
        data_dict[key] = form[key]

    # class-specific extractions
    if mclass == DataFormat:
        data_dict['is_open'] = 'is_open' in form.keys()
    elif mclass == Person:
        data_dict['affiliation'] = form.getlist('affiliation')
        data_dict['contact_org'] = form.getlist('contact_org')
        data_dict['contact_dataset'] = form.getlist('contact_dataset')
        data_dict['contributor_dataset'] = form.getlist('contributor_dataset')
    elif mclass == ResourceCategoryMetadataItem:
        # only store enumeration items if the datatype is actually an
        # enumeration
        if data_dict['datatype'] != "ENUM":
            data_dict['enum_items'] = None

    return data_dict


def _display_person(id):

    data = _person_show({'session': Session}, {'id': id})
    return render('view_person.html', data)


def _display_publication(id):

    data = _publication_show({'session': Session}, {'id': id})
    return render('view_publication.html', data)


def _display_dataformat(id):

    data = _data_format_show({'session': Session}, {'id': id})

    # add datasets to referenced resources
    data['resources'] = \
        [(x, Session.query(model.package.Package).get(x.package_id))
         for x in data['resources']]

    return render('view_dataformat.html', data)


def _display_license(id):

    data = _license_show({'session': Session}, {'id': id})
    return render('view_license.html', data)


def _display_dataformat_list():

    itemlist = [(x.id,
                 x.name,
                 h.url_for('cdsmetadata.view_dataformat', id=x.id))
                for x in Session.query(DataFormat).all()]

    data = {'items': sorted(itemlist, key=lambda tup: tup[1]),
            'title': 'All currently registered dataformats',
            'sidebar_header': "Dataformat list",
            'sidebar_text': "A list of all dataformats \
                             currently registered in the portal."}

    return render('view_metadata_list.html', data)


def _display_publication_list():

    itemlist = [(x.id,
                x.name,
                h.url_for('cdsmetadata.view_publication', id=x.id))
                for x in Session.query(Publication).all()]
    data = {'items': sorted(itemlist, key=lambda tup: tup[1]),
            'title': 'All currently registered publications',
            'sidebar_header': "Publication list",
            'sidebar_text': "A list of all publications \
                             currently registered in the portal."}

    return render('view_metadata_list.html', data)


def _display_license_list():

    itemlist = [(x.id,
                x.name,
                h.url_for('cdsmetadata.view_license', id=x.id))
                for x in Session.query(License).all()]
    data = {'items': sorted(itemlist, key=lambda tup: tup[1]),
            'title': 'All currently registered licenses',
            'sidebar_header': "License list",
            'sidebar_text': "A list of all licenses \
                             currently registered in the portal."}

    return render('view_metadata_list.html', data)


def _display_person_list():

    itemlist = [(x.id,
                x.name,
                h.url_for('cdsmetadata.view_person_info', id=x.id))
                for x in Session.query(Person).all()]
    data = {'items': sorted(itemlist, key=lambda tup: tup[1]),
            'title': 'All currently registered persons',
            'sidebar_header': "Person list",
            'sidebar_text': "A list of all persons registered \
                             as having roles related to datasets \
                             or organizations referenced in the portal."}

    return render('view_metadata_list.html', data)


def _display_resource_categories():

    data = _list_all_categories()
    return render('view_categories.html', data)


def _category_dict():

    categories = Session.query(ResourceCategory).all()

    return {x.code: x.title for x in categories}


def _list_all_categories():

    categories = Session.query(ResourceCategory).all()

    result = {'categories':
              sorted([(x.code, x.title, x.description.splitlines())
                      for x in categories],
                     key=lambda tup: tup[0])}
    return result


def _list_all_category_metadata():

    data_items = Session.query(ResourceCategoryMetadataItem).all()

    return sorted(
        [(x.category_id, x.title, x.datatype, x.description,
          None if x.enum_items is None else
          [{'value': y, 'text': y}
           for y in map(unicode.strip, x.enum_items.split(','))])
         for x in data_items],
        key=lambda tup: tup[0])


def _list_category_metadata_items_for(code, preformat=False):

    if code is None:
        return None

    items = get_required_metadata_fields(code)
    # items = Session.query(ResourceCategoryMetadataItem).\
    #         filter_by(category_id=code)

    if preformat:
        return [x.title.replace('_', ' ') for x in items]
    else:
        return [x.title for x in items]


def _edit_metadata(mclass, template_name):

    check_edit_metadata()  # check authorization

    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': g.userobj}

    g.pkg_dict = request.params
    id = g.pkg_dict.get('id', None)
    g.cur_item = None
    g.template_name = template_name

    if request.method == 'POST':

        if 'save' in request.form:

            data_dict = _extract_metadata_form_data(request.form, mclass)

            # run validation if validation function is present
            data_ok = True
            if _validation_function(mclass) is not None:
                try:
                    data_dict = _validation_function(mclass)(data_dict)
                except ValidationError as e:
                    id = request.form.get('save', None)
                    g.pkg_dict = {'id': id} if id else {'new': True}
                    g.cur_item = data_dict
                    g.errors = e.error_dict
                    g.error_summary = e.error_summary
                    data_ok = False

            # update database
            if data_ok:
                if data_dict['id']:
                    tk.get_action(_update_fun(mclass))(context, data_dict)
                else:
                    tk.get_action(_create_fun(mclass))(context, data_dict)

        elif 'delete' in request.params:
            # due to a quirk in the JavaScript handing of "confirm-action", the
            # returned form will be empty.  The dataset id will however still
            # be available from the url.  We therefore use request.params
            # rather than request.form here.
            id = request.params['id']
            tk.get_action(_delete_fun(mclass))(context, {'id': id})
            return tk.redirect_to(request.base_url)

    if id and (g.cur_item is None):
        show_fun = tk.get_action(_show_fun(mclass))
        g.cur_item = show_fun(context, {'id': id})

    g.extra = _extra_info(mclass, g.cur_item)  # class-specific info

    g.items = \
        sorted([(x.id, x.name)
                for x in context['session'].query(mclass).all()],
               key=lambda tup: tup[1].lower())

    return render(template_name + '.html')


def _show_package_schema(schema):

    schema.update({
        'contact_person': [tk.get_validator('ignore_missing'),
                           tk.get_converter('convert_to_list_if_string')],
        'person_contributor': [tk.get_validator('ignore_missing'),
                               tk.get_converter('convert_to_list_if_string')],
        'org_contributor': [tk.get_validator('ignore_missing'),
                            tk.get_converter('convert_to_list_if_string')],
        'publications': [tk.get_validator('ignore_missing'),
                         tk.get_converter('convert_to_list_if_string')],
        'related_dataset': [tk.get_validator('ignore_missing'),
                            tk.get_converter('convert_to_list_if_string')],
        'doi': [tk.get_converter('convert_from_extras'),
                tk.get_validator('ignore_missing'),
                tk.get_validator('check_doi')],
        'project_type': [tk.get_converter('convert_from_extras'),
                         tk.get_validator('project_type_validator')],
        'access_level': [tk.get_converter('convert_from_extras'),
                         tk.get_validator('access_level_validator')],
        'release_date': [tk.get_converter('convert_from_extras')],
        'temporal_coverage_start': [
            tk.get_converter('convert_from_extras'),
            tk.get_validator('temporal_coverage_nonnegative')],
        'temporal_coverage_end': [tk.get_converter('convert_from_extras')],
        'cdslicense': [tk.get_converter('convert_from_extras'),
                       tk.get_validator('ignore_missing')],
        'location': [tk.get_converter('convert_from_extras'),
                     tk.get_validator('wgs84-validator')]
    })
    schema['resources'].update({
        'category': [tk.get_validator('category_exists')],
        'purpose': [tk.get_validator('ignore_missing')],
        'sources': [tk.get_validator('ignore_missing'),
                    tk.get_validator('validate_sources')],
        'assumptions': [tk.get_validator('ignore_missing')],
        'dataformat': [tk.get_validator('ignore_missing'),
                       tk.get_validator('dataformat_exists')]
    })

    return schema


def _modif_package_schema(schema):

    # reusing the schema from _show_package_schema, with certain modifications
    schema = _show_package_schema(schema)

    schema['doi'] = [tk.get_validator('ignore_missing'),
                     tk.get_validator('check_doi'),
                     tk.get_converter('convert_to_extras')]

    schema['project_type'] = [tk.get_validator('project_type_validator'),
                              tk.get_converter('convert_to_extras')]

    schema['access_level'] = [tk.get_validator('access_level_validator'),
                              tk.get_converter('convert_to_extras')]
    schema['release_date'] = [tk.get_converter('convert_to_extras')]

    schema['temporal_coverage_start'] = \
        [tk.get_validator('temporal_coverage_nonnegative'),
         tk.get_converter('convert_to_extras')]
    schema['temporal_coverage_end'] = \
        [tk.get_validator('temporal_coverage_nonnegative'),
         tk.get_converter('convert_to_extras')]
    schema['cdslicense'] = [tk.get_validator('ignore_missing'),
                            tk.get_converter('convert_to_extras')]
    schema['location'] = [tk.get_validator('wgs84-validator'),
                          tk.get_converter('convert_to_extras')]

    # for now, there is no difference between the show and the modif schemas
    return schema


def _package_after_update(context, pkg_dict):

    pkg = meta.Session.query(model.package.Package).get(pkg_dict['id'])

    # contact person
    pkg.contact_person = \
        _list_people(context['session'],
                     pkg_dict.get('contact_person', []))

    # contributor person
    pkg.person_contributor = \
        _list_people(context['session'],
                     pkg_dict.get('person_contributor', []))

    # contributor organization

    orgs = _list_orgs(context['session'],
                      pkg_dict.get('org_contributor', []))

    pkg.org_contributor = [x.extra for x in orgs]

    # associated publications
    pkg.publications = \
        _list_pubs(context['session'],
                   pkg_dict.get('publications', []))

    # associated datasets
    pkg.related_dataset = \
        _list_datasets(context['session'],
                       pkg_dict.get('related_dataset', []))


def _package_before_view(pkg_dict):

    pkg = model.package.Package.get(pkg_dict['id'])

    pkg_dict['contact_person'] = \
        [(x.id, x.name, x.email) for x in pkg.contact_person]

    pkg_dict['person_contributor'] = \
        [(x.id, x.name, x.email) for x in pkg.person_contributor]

    pkg_dict['org_contributor'] = \
        [(x.organization.id, x.organization.title)
         for x in pkg.org_contributor]

    pkg_dict['publications'] = \
        [(x.id, x.name, x.doi) for x in pkg.publications]

    pkg_dict['related_dataset'] = \
        [(x.id, x.title) for x in pkg.related_dataset]

    return pkg_dict

# ========================= Validator implementations =========================


def _check_doi(value, context):
    if value is None:
        return None

    if (len(value) >= 4 and value.lower()[0:4] == 'http') or \
       (len(value) >= 3 and value.lower()[0:3] == 'doi') or \
       value.lower().find('doi.org') != -1:
        raise Invalid(_('Please do not include http or doi part of doi'))

    return value


def _project_type_validator(value, context):

    if value is None:
        return None  # normally shouldn't happen
    if value not in CdsmetadataPlugin.project_types:
        raise Invalid(_('Invalid project type.  Valid types are: "' +
                        '", "'.join(CdsmetadataPlugin.project_types) + '".'))
    return value


def _access_level_validator(value, context):

    if value is None:
        return None  # normally shouldn't happen
    if value not in CdsmetadataPlugin.access_levels:
        raise Invalid(_('Invalid access level.  Valid types are: "' +
                        '", "'.join(CdsmetadataPlugin.access_levels) + '".'))
    return value


def _temporal_coverage_nonnegative(key, data, errors, context):

    start = data.get(('temporal_coverage_start',), None)
    end = data.get(('temporal_coverage_end',), None)

    if start and end:
        start_date = dateutil.parser.parse(start)
        end_date = dateutil.parser.parse(end)

        if start_date > end_date:
            raise Invalid(
                _("Invalid date range; start date is after end date."))

def _wgs84_validator(value, context):

    if type(value) == list and len(value) == 2:
        # this is likely a data object that has been previously validated
        lon, lat = value
    else:
        # this is text coming right from user input
        try:
            lon, lat = map(float, value.strip('[](){}').split(','))
        except:
            raise Invalid(_("Wrong input format.  Use: 'lon, lat'"))

    if lon < -180 or lon > 180:
        raise Invalid(_("Longitude should be in [-180, 180]"))

    if lat < -90 or lat > 90:
        raise Invalid(_("Latitude should be in [-90, 90]"))

    return [lon, lat]

def _category_exists_validator(value, context):
    if type(value) == Missing:
        # @@ The value shouldn't really be missing, this is a stopgap
        # hack to allow development on an outdated database.
        return u'1.0.0'
    elif context['session'].query(ResourceCategory).get(value) is None:
        raise Invalid("Chosen resource category does not exist.")

    return value


def _dataformat_exists_validator(value, context):

    found = context['session'].query(DataFormat).get(value)

    if not found:
        raise Invalid("Dataformat does not exist.")

    return value

def _sources_validator(value):

    # check if a source list can be made, but do not use it
    _make_sourcelist(value)

    return value


def _make_sourcelist(value):

    lines = value.splitlines()

    result = []
    for num, l in enumerate(lines):
        try:
            name, uri = [x.strip() for x in l.split(',')]
        except:
            raise Invalid('Input format error on line {0}'.format(num+1))
        result.append([name, uri])

    return result


class CdsmetadataPlugin(plugins.SingletonPlugin,
                        tk.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IDatasetForm, inherit=True)

    # ================================== IFacets ==============================

    def dataset_facets(self, facets_dict, package_type):

        # remove facets we don't use (or that we have redefined)
        facets_dict.pop('groups')  # we do not use groups
        facets_dict.pop('license_id')  # we have redefined licenses
        facets_dict.pop('res_format')  # we have redefined formats

        # add new facets
        facets_dict['project_type'] = _('Project type')
        facets_dict['category'] = _('Data category')
        facets_dict['dataformat'] = _('Data format')

        return facets_dict

    def organization_facets(self, facets_dict,
                            organization_type, package_type):
        return self.dataset_facets(facets_dict, package_type)

    # ================================== IRoutes ==============================

    def before_map(self, map):
        map.connect('edit_dataformat', '/metadata/dataformat',
                    action='edit_dataformat', controller='cdsmetadata')
        map.connect('edit_license', '/metadata/license',
                    action='edit_license', controller='cdsmetadata')
        map.connect('edit_publication', '/metadata/publication',
                    action='edit_publication', controller='cdsmetadata')
        map.connect('edit_person', '/metadata/person',
                    action='edit_person', controller='cdsmetadata')
        map.connect('edit_category_metadata', '/metadata/category_metadata',
                    action='edit_category_metadata', controller='cdsmetadata')
        return map

    def after_map(self, map):
        return map

    # ============================== IAuthFunctions ===========================
    def get_auth_functions(self):
        return{'edit_metadata': _edit_metadata_auth}

    # ================================ IBlueprint =============================

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        # -------------------------- edit metadata functions ------------------
        blueprint.add_url_rule('/metadata/dataformat',
                               view_func=_edit_dataformat,
                               methods=['GET', 'POST'])
        blueprint.add_url_rule('/metadata/license',
                               view_func=_edit_license,
                               methods=['GET', 'POST'])
        blueprint.add_url_rule('/metadata/publication',
                               view_func=_edit_publication,
                               methods=['GET', 'POST'])
        blueprint.add_url_rule('/metadata/person',
                               view_func=_edit_person,
                               methods=['GET', 'POST'])
        blueprint.add_url_rule('/metadata/category_metadata',
                               view_func=_edit_category_metadata,
                               methods=['GET', 'POST'])

        # ---------------------- view individual metadata items ---------------
        blueprint.add_url_rule('/view/person/<id>',
                               u'view_person_info',
                               view_func=_display_person)
        blueprint.add_url_rule('/view/publication/<id>',
                               u'view_publication',
                               view_func=_display_publication)
        blueprint.add_url_rule('/view/dataformat/<id>/',
                               u'view_dataformat',
                               view_func=_display_dataformat)
        blueprint.add_url_rule('/view/license/<id>',
                               u'view_license',
                               view_func=_display_license)

        # ----- list categories/persons/publications/dataformats/ licenses ----
        blueprint.add_url_rule('/view/resource_categories',
                               u'resource_categories',
                               view_func=_display_resource_categories)
        blueprint.add_url_rule('/metadata/publication_list',
                               u'publication_list',
                               view_func=_display_publication_list)
        blueprint.add_url_rule('/metadata/dataformat_list',
                               u'dataformat_list',
                               view_func=_display_dataformat_list)
        blueprint.add_url_rule('/metadata/license_list',
                               u'license_list',
                               view_func=_display_license_list)
        blueprint.add_url_rule('/metadata/person_list',
                               u'person_list',
                               view_func=_display_person_list)
        return blueprint

    # ================================= IActions ==============================
    def get_actions(self):

        result = {}

        # since a plugin cannot at the same time be an IOrganizationController
        # and an IPackageController (clash of function names), we use the below
        # wrapping mechanism to add functionality to the creation, update and
        # showing of organizations.
        for aname in ['organization_create', 'organization_update']:
            result[aname] = _organization_modif_wrapper(aname)
        result['organization_show'] = _organization_show_wrapper()

        result['dataformat_create'] = _data_format_create
        result['dataformat_update'] = _data_format_update
        result['dataformat_show'] = _data_format_show
        result['dataformat_delete'] = _data_format_delete

        result['license_create'] = _license_create
        result['license_update'] = _license_update
        result['license_show'] = _license_show
        result['license_delete'] = _license_delete

        result['publication_create'] = _publication_create
        result['publication_update'] = _publication_update
        result['publication_show'] = _publication_show
        result['publication_delete'] = _publication_delete

        result['person_create'] = _person_create
        result['person_update'] = _person_update
        result['person_show'] = _person_show
        result['person_delete'] = _person_delete

        result['category_metadata_create'] = _category_metadata_create
        result['category_metadata_update'] = _category_metadata_update
        result['category_metadata_show'] = _category_metadata_show
        result['category_metadata_delete'] = _category_metadata_delete

        return result

    # ============================= ITemplateHelpers ==========================

    def get_helpers(self):

        return {'personlist': lambda l: _personlist([x[0] for x in l]),
                'orglist': lambda l: _orglist([x[0] for x in l]),
                'dsetlist': lambda l, o=[]: _dsetlist([x[0] for x in l], o),
                'publist': lambda l: _publist([x[0] for x in l]),
                'project_types': lambda: [{'text': x, 'value': x}
                                          for x in self.project_types],
                'access_levels': lambda: [{'text': x, 'value': x}
                                          for x in self.access_levels],
                'licenselist': lambda: _licenselist(),
                'dataformatlist': _dataformatlist,
                'get_license': _get_license,
                'date_today': lambda: datetime.date.today(),
                'str_2_date': lambda str: dateutil.parser.parse(str),
                'datasets_with_license': _datasets_with_license,
                'category_name': _category_name,
                'dataformat_name': _dataformat_name,
                'resource_categories': lambda: [{'value': x[0],
                                                 'text': x[0] + ' - ' + x[1]}
                                                for x in _list_all_categories()[
                                                        'categories']],
                'resource_category_items': _list_all_category_metadata,
                'category_items_for': _list_category_metadata_items_for,
                'sourcelist': _make_sourcelist
                }

    # =============================== IConfigurable ===========================
    def configure(self, config):
        # prepares all the necessary data tables
        setup_model()

        # register the new resource fields
        tk.get_action('config_option_update')({'ignore_auth': True},
                        {'ckan.extra_resource_fields':
                         'category purpose sources assumptions dataformat'})

    # ================================ IConfigurer ============================

    def update_config(self, config_):

        tk.add_template_directory(config_, 'templates')
        tk.add_resource('fanstatic', 'cdsmetadata')
        # tk.add_public_directory(config_, 'public')

    def update_config_schema(self, schema):

        ignore_missing = tk.get_validator('ignore_missing')
        schema.update({'ckan.extra_resource_fields': [ignore_missing]})
        return schema

    # ============================ IPackageController =========================

    def after_create(self, context, pkg_dict):
        _package_after_update(context, pkg_dict)

    def after_update(self, context, pkg_dict):
        _package_after_update(context, pkg_dict)

    def before_view(self, pkg_dict):
        return _package_before_view(pkg_dict)

    def after_search(self, search_results, search_params):

        # fixing display names of the category search facets

        try:
            category_facets = \
                search_results['search_facets']['category']['items']
        except KeyError:
            # the category was not found, set to empty dictionary
            category_facets = {}

        cdict = _category_dict()

        for c in category_facets:
            key = c['display_name']
            c['display_name'] = key + ' - ' + cdict[key]

        return search_results

    def before_index(self, pkg_dict):

        dataformat_names = []
        dformats = pkg_dict.get('res_extras_dataformat', [])

        for df in dformats:
            df_obj = model.Session.query(DataFormat).get(df)
            if df_obj:
                dataformat_names.append(df_obj.name)

        pkg_dict['dataformat'] = dataformat_names
        pkg_dict['category'] = pkg_dict.get('res_extras_category', '')
        return pkg_dict

    # ================================ IValidators ============================

    def get_validators(self):

        return {
            'check_doi': _check_doi,
            'project_type_validator': _project_type_validator,
            'access_level_validator': _access_level_validator,
            'wgs84-validator': _wgs84_validator,
            'category_exists': _category_exists_validator,
            'validate_sources': _sources_validator,
            'dataformat_exists': _dataformat_exists_validator,
            'temporal_coverage_nonnegative': _temporal_coverage_nonnegative
        }

    # =============================== IDatasetForm ============================

    # we store allowed options here, which will be used by specific validators
    project_types = ['Pilot', 'Commercial', 'Other']
    access_levels = ['Open', 'Restricted']

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    def create_package_schema(self):
        schema = super(CdsmetadataPlugin, self).create_package_schema()
        return _modif_package_schema(schema)

    def update_package_schema(self):
        schema = super(CdsmetadataPlugin, self).update_package_schema()
        return _modif_package_schema(schema)

    def show_package_schema(self):
        schema = super(CdsmetadataPlugin, self).show_package_schema()
        return _show_package_schema(schema)
