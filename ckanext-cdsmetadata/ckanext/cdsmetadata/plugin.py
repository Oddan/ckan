import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from flask import Blueprint
from ckan import model
from ckan.model import meta, Session
from ckan.model.types import make_uuid
from ckan.common import request, g, _
from sqlalchemy import types, Table, Column, ForeignKey, orm
from sqlalchemy.types import UnicodeText, Unicode, Boolean
import ckan.logic as logic
import ckan.logic.schema as _schema
from six import text_type
from ckan.views import api
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.base import abort, render

import copy
import pdb

TITLE_MAX_L = 100
NAME_MAX_L = 100
EMAIL_MAX_L = 500

data_format_table = None
license_table = None
publication_table = None
person_table = None
# user_extra_table = None # @@ remove
organization_extra_table = None


affiliation_association_table = None  # associate Person with Organization
contact_org_association_table = None  # associate contact Person with Organization
contact_dataset_association_table = None # associate contact with Dataset
person_contributor_dataset_association_table = None # contributor (Person) with dataset
org_contributor_dataset_association_table = None # contributor (Organization) with dataset

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
    

# @@ remove
class UserExtra(model.domain_object.DomainObject):
    def __init__(self, first_name, last_name, user_id):
        self.first_name = first_name
        self.last_name = last_name
        self.user_id = user_id


class DataFormat(model.domain_object.DomainObject):
    def __init__(self, name, is_open, description):
        self.name = name
        self.is_open = is_open
        self.description = description


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
    # prepare_user_extra_table() # @@ remove
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
        meta.mapper(Publication, publication_table)

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

# # @@ delete
# def prepare_user_extra_table():

#     global user_extra_table
#     if user_extra_table is None:
#         user_extra_table = Table(
#             'user_extra', meta.metadata,
#             Column('id', UnicodeText, primary_key=True, default=make_uuid),
#             Column('first_name', UnicodeText, nullable=False),
#             Column('last_name', UnicodeText, nullable=False),
#             Column('user_id', UnicodeText, ForeignKey('user.id'))
#         )

#         meta.mapper(UserExtra, user_extra_table,
#                     properties={'user':
#                                 orm.relation(model.user.User,
#                                              backref=orm.backref(
#                                                  'extra',
#                                                  uselist=False,
#                                                  cascade='all, delete, delete-orphan'))})

#     ensure_table_created(user_extra_table)


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

# @@ this will have to change


def _organization_modif_wrapper(action_name):

    action = tk.get_action(action_name)

    def _wrapper(context, data_dict):

        homepageURL = data_dict.get('homepageURL', '')

        result_dict = action(context, data_dict)

        # updating the extra information
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
                           data_dict.get('dataset_contributions'))

        new_extra.save()

        return result_dict

    return _wrapper


# def _user_modif_wrapper(action_name):

#     action = tk.get_action(action_name)

#     def _wrapper(context, data_dict):

#         first_name = data_dict.get('first_name', '')
#         last_name = data_dict.get('last_name', '')

#         # sync 'fullname' with 'first_name' and last_name'
#         if 'fullname' not in data_dict.keys():
#             data_dict['fullname'] = '{0} {1}'.format(first_name, last_name)

#         result_dict = action(context, data_dict)

#         result_dict['first_name'] = first_name
#         result_dict['last_name'] = last_name

#         # updating the extra information (not found in the original user
#         # object)

#         new_extra = model.User.get(result_dict['id']).extra
#         if new_extra is None:
#             new_extra = UserExtra(first_name, last_name, result_dict['id'])
#         else:
#             new_extra.first_name = first_name
#             new_extra.last_name = last_name
#         new_extra.save()

#         return result_dict

#     return _wrapper


# # @@ must change
# def _user_show_wrapper():

#     action = tk.get_action('user_show')

#     def _wrapper(context, data_dict):

#         result_dict = action(context, data_dict)
#         extra = model.User.get(result_dict['id']).extra
#         if extra is not None:
#             result_dict['first_name'] = extra.first_name
#             result_dict['last_name'] = extra.last_name

#         return result_dict

#     return _wrapper


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
                [(x.id, x.title) for x in new_extra.datasets_contributed_to]

        if result_dict['contact_person'] is not None:
            result_dict['contact_person'].sort(key=lambda x: x[1])
        result_dict['contact_person_listitems'] = \
            _personlist([x[0] for x in result_dict.get('contact_person', [])])

        if result_dict['people'] is not None:
            result_dict['people'].sort(key=lambda x: x[1])
        result_dict['people_listitems'] = \
            _personlist([x[0] for x in result_dict.get('people', [])])

        result_dict['dataset_contributions_listitems'] = \
            _dsetlist([x[0] for x in result_dict.get('datasets_contributed_to', [])])

        return result_dict

    return _wrapper


# @@ this function at present only used when listing members of an org.
# Must be adapted to refer to a Person object rather than a CKAN User
# def _username_helper_fun(user, maxlength=0):
#     if not isinstance(user, model.User):
#         user_name = text_type(user)
#         result = user_name
#         user = model.User.get(user_name)
#         if user:
#             result = user.name
#     else:
#         result = user.name

#     if maxlength and len(result) > maxlength:
#         result = result[:maxlength] + '...'

#     return result


# # @@ Used in organization form to facilitate designation of contact person.
# # Will have to change.
# def autocomplete_filtered():

#     q = request.args.get(u'q', u'')
#     org_id = request.args.get(u'org_id', u'')
#     limit = request.args.get(u'limit', 20)
#     user_list = []
#     if q:
#         context = {u'model': model, u'session': model.Session,
#                    u'user': g.user, u'auth_user_obj': g.userobj}

#         data_dict = {u'q': q, u'limit': limit}

#         # get list with matching user names
#         user_list = tk.get_action(u'user_autocomplete')(context,
#                                                         data_dict)

#         # narrow down to list of users who are actual members
#         if org_id:
#             member_list = tk.get_action('member_list')(
#                 {'model': model}, {'id': org_id})
#             member_ids = [x[0] for x in member_list]
#             user_list = [u for u in user_list if u['id'] in member_ids]

#     return api._finish_ok(user_list)


# # @@ This must change to refer to the new Person table, not to users
# def contact_person_validator(value, context):

#     org_id = context['group'].id
#     member_list = tk.get_action('member_list')(
#         {'model': model}, {'id': org_id})
#     member_ids = [x[0] for x in member_list]

#     user = model.User.by_name(value)
#     if user is None:
#         raise Invalid(_('Unknown user entered as contact person.'))

#     if user.id not in member_ids:
#         raise Invalid(_('Specified user is not member of the organization.'))

#     return value


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
    return obj if isinstance(obj, list) else [obj]



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
    tk.check_access('edit_metadata', context, data_dict)
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
    tk.check_access('edit_metadata', context, data_dict)
    pub = context['session'].query(Publication).get(data_dict['id'])
    if pub is None:
        raise tk.ObjectNotFound

    return {'name': pub.name,
            'citation': pub.citation,
            'doi': pub.doi}


def _license_show(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)
    lic = context['session'].query(License).get(data_dict['id'])
    if lic is None:
        raise tk.ObjectNotFound

    return {'name': lic.name,
            'description': lic.description,
            'license_url': lic.license_url}


def _data_format_show(context, data_dict):
    tk.check_access('edit_metadata', context, data_dict)

    df = context['session'].query(DataFormat).get(data_dict['id'])
    if df is None:
        raise tk.ObjectNotFound

    return {'name': df.name,
            'is_open': df.is_open,
            'description': df.description}


def _edit_person():
    return _edit_metadata(Person, "edit_person")


def _edit_dataformat():
    return _edit_metadata(DataFormat, "edit_dataformat")


def _edit_license():
    return _edit_metadata(License, "edit_license")


def _edit_publication():
    return _edit_metadata(Publication, "edit_publication")


def _update_fun(mclass):
    return {Person: 'person_update',
            DataFormat: 'dataformat_update',
            License: 'license_update',
            Publication: 'publication_update'}[mclass]


def _create_fun(mclass):
    return {Person: 'person_create',
            DataFormat: 'dataformat_create',
            License: 'license_create',
            Publication: 'publication_create'}[mclass]


def _delete_fun(mclass):
    return {Person: 'person_delete',
            DataFormat: 'dataformat_delete',
            License: 'license_delete',
            Publication: 'publication_delete'}[mclass]


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

    orgs = model.Session.query(model.group.Group).all()
    orglist = \
        [{'value': x.id, 'text': x.title, 'selected': False} for x in orgs]
    orglist.sort(key=lambda x: x['text'])

    # set selection
    for o in orglist:
        if o['value'] in selected_ids:
            o['selected'] = True

    return orglist


def _dsetlist(selected_ids):

    datasets = model.Session.query(model.package.Package).all()
    dsetlist = \
        [{'value': x.id, 'text': x.title, 'selected': False} for x in datasets]
    dsetlist.sort(key=lambda x: x['text'])

    # set selection
    for d in dsetlist:
        if d['value'] in selected_ids:
            d['selected'] = True

    return dsetlist


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
    else:
        return {DataFormat: None,
                License: None,
                Publication: None}[mclass]


def _show_fun(mclass):
    return {Person: 'person_show',
            DataFormat: 'dataformat_show',
            License: 'license_show',
            Publication: 'publication_show'}[mclass]


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
    if mclass == Person:
        data_dict['affiliation'] = form.getlist('affiliation')
        data_dict['contact_org'] = form.getlist('contact_org')
        data_dict['contact_dataset'] = form.getlist('contact_dataset')
        data_dict['contributor_dataset'] = form.getlist('contributor_dataset')

    return data_dict


def _edit_metadata(mclass, template_name):
    check_edit_metadata()  # check authorization

    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': g.userobj}

    if request.method == 'POST':

        if 'save' in request.form:
            data_dict = _extract_metadata_form_data(request.form, mclass)
            if data_dict['id']:
                tk.get_action(_update_fun(mclass))(context, data_dict)
            else:
                tk.get_action(_create_fun(mclass))(context, data_dict)
        elif 'delete' in request.params:
            # due to a quirk in the JavaScript handing of "confirm-action", the
            # returned form will be empty.  The dataset id will however still be
            # available from the url.  We therefore use request.params rather
            # than request.form here.
            id = request.params['id']
            tk.get_action(_delete_fun(mclass))(context, {'id': id})
            return tk.redirect_to(request.base_url)

    g.pkg_dict = request.params
    g.cur_item = None
    g.template_name = template_name

    id = request.params.get('id', None)
    if id:
        show_fun = tk.get_action(_show_fun(mclass))
        g.cur_item = show_fun(context, {'id': id})

    g.extra = _extra_info(mclass, g.cur_item)  # class-specific info

    g.items = \
        sorted([(x.id, x.name) for x in context['session'].query(mclass).all()],
               key=lambda tup: tup[1].lower())

    return render(template_name + '.html')


class CdsmetadataPlugin(plugins.SingletonPlugin,
                        tk.DefaultOrganizationForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IActions)
    # plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IBlueprint)
    # plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IRoutes)
    # plugins.implements(plugins.IGroupForm)

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
        return map

    def after_map(self, map):
        return map

    # ============================== IAuthFunctions ===========================
    def get_auth_functions(self):
        return{'edit_metadata': _edit_metadata_auth}

    # # ================================ IValidators ============================
    # def get_validators(self):

    #     return {'valid_contact_person': contact_person_validator}

    # ================================ IBlueprint =============================

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        # blueprint.add_url_rule('/api/co2datashare/autocomplete_filtered',
        #                        view_func=autocomplete_filtered)
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
        return blueprint

    # # ============================= ITemplateHelpers ==========================
    # def get_helpers(self):
    #     # @@ currently only used when list
    #     return {'username': _username_helper_fun}

    # ================================= IActions ==============================
    def get_actions(self):

        result = {}
        # for aname in ['user_create', 'user_update']:
        #     result[aname] = _user_modif_wrapper(aname)

        # result['user_show'] = _user_show_wrapper()

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

        return result

    # =============================== IConfigurable ===========================
    def configure(self, config):
        # prepares all the necessary data tables
        setup_model()

    # ================================ IConfigurer ============================

    def update_config(self, config_):

        tk.add_template_directory(config_, 'templates')
        tk.add_resource('fanstatic', 'cdsmetadata')
        # tk.add_public_directory(config_, 'public')

    # # ================================ IGroupForm =============================
    # is_organization = True

    # def is_fallback(self):

    #     return True

    # def group_types(self):

    #     return []

    # def group_controller(self):

    #     pass

    # def form_to_db_schema(self):

    #     schema = super(CdsmetadataPlugin, self).form_to_db_schema()
    #     schema.update({'homepageURL': [
    #                         tk.get_validator('ignore_missing'),
    #                         tk.get_converter('convert_to_extras')
    #                                   ]})
    #     return schema

    # def db_to_form_schema(self):
    #     schema = self._default_show_group_schema()

    #     schema.update({'homepageURL': [
    #         tk.get_converter('convert_from_extras'),
    #         tk.get_validator('ignore_missing')
    #     ]})
    #     return schema

    # def _default_show_group_schema(self):
    #     schema = _schema.default_group_schema()

    #     # make default show schema behave like when run with no validation
    #     schema['num_followers'] = []
    #     schema['created'] = []
    #     schema['display_name'] = []
    #     # schema['extras'] = {'__extras': [keep_extras]}  # has to be removed, or extras won't work
    #     schema['package_count'] = [tk.get_validator('ignore_missing')]
    #     schema['packages'] = {'__extras': [tk.get_validator('keep_extras')]}
    #     schema['revision_id'] = []
    #     schema['state'] = []
    #     schema['users'] = {'__extras': [tk.get_validator('keep_extras')]}

    #     return schema




# def _orglist(person_data):

#     orgs = model.Session.query(model.group.Group).all()
#     orglist = \
#         [{'value': x.id, 'text': x.title, 'selected': False} for x in orgs]
#     orglist.sort(key=lambda x: x['text'])

#     # prepare list where all current affiliations are selected
#     afflist = \
#         [] if person_data is None else [x[0] for x in person_data['affiliation']]
#     orglist_aff = copy.deepcopy(orglist) 

#     for o in orglist_aff:
#         if o['value'] in afflist:
#             o['selected'] = True

#     # prepare list where all current contact organizations are listed
#     contact_list = \
#         [] if person_data is None else [x[0] for x in person_data['contact_org']]
#     orglist_contact = copy.deepcopy(orglist)
#     for o in orglist_contact:
#         if o['value'] in contact_list:
#             o['selected'] = True

#     return {'orglist_aff': orglist_aff, 'orglist_contact': orglist_contact}


# def _dsetlist(person_data):

#     datasets = model.Session.query(model.package.Package).all()
#     dsetlist = \
#         [{'value': x.id, 'text': x.title, 'selected': False} for x in datasets]
#     dsetlist.sort(key=lambda x: x['text'])

#     # prepare list where all current contact datasets are listed
#     contact_list = \
#         [] if person_data is None \
#         else [x[0] for x in person_data['contact_dataset']]

#     dsetlist_contact = copy.deepcopy(dsetlist)
#     for d in dsetlist_contact:
#         if d['value'] in contact_list:
#             d['selected'] = True

#     # prepare list where all current contributor datasets are listed
#     contributor_list = \
#         [] if person_data is None \
#         else [x[0] for x in person_data['contributor_dataset']]

#     dsetlist_contributor = copy.deepcopy(dsetlist)
#     for d in dsetlist_contributor:
#         if d['value'] in contributor_list:
#             d['selected'] = True

#     return {'dsetlist_contact': dsetlist_contact,
#             'dsetlist_contributor': dsetlist_contributor}
    
