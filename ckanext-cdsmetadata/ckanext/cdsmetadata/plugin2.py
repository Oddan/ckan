import ckan.plugins as plugins
# from plugin import ResourceExtra
# from ckan import model
# from ckan.model import meta, Session
# from resource_category import ResourceCategory

# import pdb

def _resource_modif(context, resource):
    pass

class CdsMetadataResourcesPlugin(plugins.SingletonPlugin):
    pass
    # plugins.implements(plugins.IResourceController)

    # def before_create(self, context, resource):
    #     u'''
    #     Extensions will receive this before a resource is created.
        
    #     :param context: The context object of the current request, this
    #         includes for example access to the ``model`` and the ``user``.
    #     :type context: dictionary
    #     :param resource: An object representing the resource to be added
    #         to the dataset (the one that is about to be created).
    #     :type resource: dictionary
    #     '''
    #     pass

    # def after_create(self, context, resource):
    #     u'''
    #     Extensions will receive this after a resource is created.

    #     :param context: The context object of the current request, this
    #         includes for example access to the ``model`` and the ``user``.
    #     :type context: dictionary
    #     :param resource: An object representing the latest resource added
    #         to the dataset (the one that was just created). A key in the
    #         resource dictionary worth mentioning is ``url_type`` which is
    #         set to ``upload`` when the resource file is uploaded instead
    #         of linked.
    #     :type resource: dictionary
    #     '''

    #     # Add extra data
    #     extra = ResourceExtra(resource['id'])
    #     extra.category_id=None#resource['category']
    #     extra.save()

    #     pass

    # def before_update(self, context, current, resource):
    #     u'''
    #     Extensions will receive this before a resource is updated.

    #     :param context: The context object of the current request, this
    #         includes for example access to the ``model`` and the ``user``.
    #     :type context: dictionary
    #     :param current: The current resource which is about to be updated
    #     :type current: dictionary
    #     :param resource: An object representing the updated resource which
    #         will replace the ``current`` one.
    #     :type resource: dictionary
    #     '''
    #     pass

    # def after_update(self, context, resource):
    #     u'''
    #     Extensions will receive this after a resource is updated.

    #     :param context: The context object of the current request, this
    #         includes for example access to the ``model`` and the ``user``.
    #     :type context: dictionary
    #     :param resource: An object representing the updated resource in
    #         the dataset (the one that was just updated). As with
    #         ``after_create``, a noteworthy key in the resource dictionary
    #         ``url_type`` which is set to ``upload`` when the resource file
    #         is uploaded instead of linked.
    #     :type resource: dictionary
    #     '''
        
    #     extra = model.Resource.get(resource['id']).extra
    #     extra.category_id = None #resource['category']
    #     extra.save()
        

    # def before_delete(self, context, resource, resources):
    #     u'''
    #     Extensions will receive this before a previously created resource is
    #     deleted.

    #     :param context: The context object of the current request, this
    #         includes for example access to the ``model`` and the ``user``.
    #     :type context: dictionary
    #     :param resource: An object representing the resource that is about
    #         to be deleted. This is a dictionary with one key: ``id`` which
    #         holds the id ``string`` of the resource that should be deleted.
    #     :type resource: dictionary
    #     :param resources: The list of resources from which the resource will
    #         be deleted (including the resource to be deleted if it existed
    #         in the package).
    #     :type resources: list
    #     '''
    #     pass

    # def after_delete(self, context, resources):
    #     u'''
    #     Extensions will receive this after a previously created resource is
    #     deleted.

    #     :param context: The context object of the current request, this
    #         includes for example access to the ``model`` and the ``user``.
    #     :type context: dictionary
    #     :param resources: A list of objects representing the remaining
    #         resources after a resource has been removed.
    #     :type resource: list
    #     '''
    #     pass

    # def before_show(self, resource_dict):
    #     u'''
    #     Extensions will receive the validated data dict before the resource
    #     is ready for display.

    #     Be aware that this method is not only called for UI display, but also
    #     in other methods like when a resource is deleted because showing a
    #     package is used to get access to the resources in a package.
    #     '''
    #     #resource_dict['category'] = "KRULL"
    #     return resource_dict


