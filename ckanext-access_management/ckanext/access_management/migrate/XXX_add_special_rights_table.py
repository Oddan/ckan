# encoding: utf-8

from sqlalchemy import *
from migrate import *
import uuid


meta = MetaData()

def make_uuid():
    return unicode(uuid.uuid4())

rights_table = Table(
    'special_access_rights', meta,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('user_id', UnicodeText, ForeignKey('user.id')))

def upgrade(migrate_engine):

    meta.bind = migrate_engine
    user_table = Table('user', meta, autoload=True)
    
    rights_table.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    rights_table.drop()
