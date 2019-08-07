from ckan.model.domain_object import DomainObject
from ckan.model import meta, Session
from ckan.model.types import make_uuid
from sqlalchemy import Table, Column, ForeignKey, orm
from sqlalchemy.types import UnicodeText, Unicode

import pdb
resource_category_table = None
CODE_LEN = 10

category_metadata_datatypes = [
    'STRING', 'INTEGER', 'INTEGERLIST', 'FLOAT', 'FLOATLIST', 'ENUM'
]


class ResourceCategory(DomainObject):
    def __init__(self, code, title, description):
        self.code = code
        self.title = title
        self.description = description

    # properties to make object compatible with other metadata objects
    @property
    def id(self):
        return self.code

    @property
    def name(self):
        return self.code + " - " + self.title


class ResourceCategoryMetadataItem(DomainObject):
    def __init__(self, title, category_id, datatype,
                 description, enum_items=None):
        self.title = title
        self.category_id = category_id
        self.datatype = datatype
        self.description = description
        self.enum_items = enum_items  # only relevant if datatype equals ENUM

    @property
    def name(self):
        return self.category.code + " - " + self.title

# =========================== Map table with class ===========================


resource_category_table = Table(
    'resource_category', meta.metadata,
    Column('code', Unicode(CODE_LEN), primary_key=True),
    Column('title', UnicodeText),
    Column('description', UnicodeText)
)

meta.mapper(ResourceCategory, resource_category_table)


ITEM_TITLE_MAX = 100
TYPE_NAME_MAX = 100

resource_category_metadata_item_table = Table(
    'resource_category_metadata_item', meta.metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('title', Unicode(ITEM_TITLE_MAX)),
    Column('category_id', UnicodeText, ForeignKey('resource_category.code')),
    Column('datatype', Unicode(TYPE_NAME_MAX)),
    Column('description', UnicodeText),
    Column('enum_items', UnicodeText)
)

meta.mapper(ResourceCategoryMetadataItem,
            resource_category_metadata_item_table,
            properties={'category':
                        orm.relationship(
                            ResourceCategory,
                            backref=orm.backref(
                                'metadata_item',
                                cascade='all, delete, delete-orphan'))})


# ========================= Create and populate table =========================


if not resource_category_table.exists():

    resource_category_table.create()

    # populate table
    Session.add(ResourceCategory(u'1.0.0', u'Technical, Geographical data', u''))
    Session.add(ResourceCategory(u'1.1.0', u'Technical data', 
                                 u'Technical data and specification on equipment, \
                                 installations, wells, wellpaths, etc.'))
    Session.add(ResourceCategory(u'1.2.0', u'Geographical data',
                                 u"""
                                 - GIS-information/maps regarding site location, \
                                 extent, well positions, etc.
                                 - regional capacity estimates
                                 - uplift data (cross-classified with field \
                                 measurement data)"""))
    Session.add(ResourceCategory(u'2.0.0', u'Measurement data', u''))
    Session.add(ResourceCategory(u'2.1.0', u'Field measurement data', u''))
    Session.add(ResourceCategory(u'2.1.1', u'Seismic measurements', u''))
    Session.add(ResourceCategory(u'2.1.2', u'Well logs', u''))
    Session.add(ResourceCategory(u'2.1.3', u'Operational data',
                                 u'E.g.: injection \
                                 schedules and associated measurements'))
    Session.add(ResourceCategory(u'2.1.4', u'Monitoring data', u''))
    Session.add(ResourceCategory(u'2.1.5', u'Other field measurement data',
                                 u"""
                                 - Includes uplift data (cross classified with \
                                 geographical data)
                                 - Other field measurement data not elsewhere described
                                 """))
    Session.add(ResourceCategory(u'2.2.0', u'Laboratory measurement data', u''))
    Session.add(ResourceCategory(u'2.2.1', u'Core sample data', u''))
    Session.add(ResourceCategory(u'2.2.2', u'Fluid analyses', u''))
    Session.add(ResourceCategory(u'2.2.3', u'Other laboratory data', u''))
    Session.add(ResourceCategory(u'3.0.0', u'Modeling data', u''))
    Session.add(ResourceCategory(u'3.1.0', u'Velocity models', u''))
    Session.add(ResourceCategory(u'3.2.0', u'Geological models',
                                 u"""
                                 - detailed 3D models of geological formations or sites
                                 - horizons, fault sticks, etc.
                                 - site-specific estimated geological properties, e.g.\
                                 geomechanical data
                                 """))
    Session.add(ResourceCategory(u'3.3.0', u'Simulation models', u''))
    Session.add(ResourceCategory(u'3.3.1', u'Reservoir simulation models and associated data',
                                 u''))
    Session.add(ResourceCategory(u'3.3.2', u'Computed simulation results', u''))
    Session.add(ResourceCategory(u'4.0.0', u'Other data',
                                 u"""
                                 - reports and other written documents for human readers
                                 - photographic images
                                 - other data not elsewhere described
                                 """))
                                 
if not resource_category_metadata_item_table.exists():
    resource_category_metadata_item_table.create()


# save all changes
Session.commit()

    
