from ckan.model.domain_object import DomainObject
from ckan.model import meta, Session
from sqlalchemy import Table, Column, ForeignKey, orm
from sqlalchemy.types import UnicodeText, Unicode

resource_category_table = None
CODE_LEN = 10

class ResourceCategory(DomainObject):
    def __init__(self, code, title, description):
        self.code = code
        self.title = title
        self.description = description

# =========================== Map table with class ===========================

resource_category_table = Table(
    'resource_category', meta.metadata,
    Column('code', Unicode(CODE_LEN), primary_key=True),
    Column('title', UnicodeText),
    Column('description', UnicodeText)
)

meta.mapper(ResourceCategory, resource_category_table)
            

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
                                 
    # save all changes
    Session.commit()

    
