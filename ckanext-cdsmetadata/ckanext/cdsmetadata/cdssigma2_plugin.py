import ckan.plugins as plugins
import ckan.lib.helpers as h
import ckan.plugins.toolkit as tk
import ckan.lib.uploader as upl

import pdb

class CdsSigma2Plugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IResourceController)

    def before_create(self, context, resource):
        pass
    
    def after_create(self, context, resource):
        upload = upl.get_resource_uploader(resource)
        filepath = upload.get_path(resource['id'])
        #pdb.set_trace()
        pass

    def before_update(self, context, current, resource):
        pass
    
    def after_update(self, context, resource):
        pass

    def before_delete(self, context, resource, resources):
        pass

    def after_delete(self, context, resources):
        pass
    
    def before_show(self, resource_dict):
        pass
