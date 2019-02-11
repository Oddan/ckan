# encoding: utf-8

from sqlalchemy import *
from migrate import *
import uuid
import pdb

meta = MetaData()

def make_uuid():
    return unicode(uuid.uuid4())

rights_table = Table(
    'special_access_rights', meta,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('user_id', UnicodeText, ForeignKey('user.id')),
    Column('package_id', UnicodeText, ForeignKey('package.id'))) 

access_restriction_table = Table(
    'access_restriction', meta,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('package_id', UnicodeText, ForeignKey('package.id'),
           unique=True, nullable=False),
    Column('restricted', Boolean, default=False),
    Column('embargo_date', DateTime, default=None))

def upgrade(migrate_engine):

    meta.bind = migrate_engine
    user_table = Table('user', meta, autoload=True)
    package_table = Table('package', meta, autoload=True)

    rights_table.create()
    access_restriction_table.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    rights_table.drop()
    access_restriction_table.drop()
