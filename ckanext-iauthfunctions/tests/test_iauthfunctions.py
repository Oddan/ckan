from nose.tools import assert_raises
from nose.tools import assert_equal

import ckan.model as model
import ckan.plugins
from ckan.plugins.toolkit import NotAuthorized, ObjectNotFound
import ckan.tests.factories as factories
import ckan.logic as logic

import ckan.tests.helpers as helpers

class TestExampleIAuthFunctionsPluginV6ParentAuthFunctions(object):
    @classmethod
    def setup_class(cls):
        ckan.plugins.load('example_iauthfunctions_v6_parent-auth_functions')
    def teardown(self):
        model.repo.rebuild_db()x
    @classmethod
    def teardown_class(cls):
        
