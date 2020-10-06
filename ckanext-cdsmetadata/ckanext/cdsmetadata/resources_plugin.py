import ckan.plugins as plugins
from ckan.model import Session
from resource_category import ResourceCategoryMetadataItem
from ckan.logic import ValidationError

# import pdb


def _add_error(error_dict, key, message):

    # ensure there is a list associated with this key
    if key not in error_dict:
        error_dict[key] = []

    error_dict[key].append(message)


def _validator_fun(datatype):
    return {'STRING': _string_validator,
            'INTEGER': _integer_validator,
            'INTEGERLIST': _integer_list_validator,
            'FLOAT': _float_validator,
            'FLOATLIST': _float_list_validator,
            'ENUM': _enum_validator}[datatype]


def _string_validator(code, title, value, errors):
    # for strings, anything is currently accepted
    pass


def _integer_validator(code, title, value, errors):
    # check that value is convertible to integer
    try:
        int(value)
    except ValueError:
        _add_error(errors, title, 'Provided value not convertible to integer.')


def _integer_list_validator(code, title, value, errors):
    # check that value is convertible to a list of integers
    try:
        map(int, value.split(','))
    except ValueError:
        _add_error(errors, title,
                   'Provided value not convertible to list of integers.')


def _float_validator(code, title, value, errors):
    # check that value is convertible to float
    try:
        float(value)
    except ValueError:
        _add_error(errors, title, 'Provided value not convertible to float.')


def _float_list_validator(code, title, value, errors):
    # check that value is convertible to a list of float
    try:
        map(float, value.split(','))
    except ValueError:
        _add_error(errors, title,
                   'Provided value not convertible to list of float.')


def _enum_validator(code, title, value, errors):

    all_codes = _code_hierarchy_of(code)

    item = None
    for cur_code in all_codes:
        item = Session.query(ResourceCategoryMetadataItem).\
               filter_by(category_id=cur_code).\
               filter_by(title=title)
        if item.count() > 0:
            assert(item.count() == 1,
                   'more than one instance of the metadata item found')
            item = list(item)[0]
            break

    enum_allowed_values = map(unicode.strip, item.enum_items.split(','))

    if value not in enum_allowed_values:
        _add_error(errors, title, 'Illegal value provided for enumeration.')


def _code_hierarchy_of(code):
    # determine codes for class and its superclasses
    lcode = list(code)
    all_codes = [code]
    if lcode[4] != '0':
        lcode[4] = '0'
        all_codes.append(''.join(lcode))
    if lcode[2] != '0':
        lcode[2] = '0'
        all_codes.append(''.join(lcode))

    return all_codes


def get_required_metadata_fields(code):

    all_codes = _code_hierarchy_of(code)

    result = []
    for code in all_codes:
        fields = Session.query(ResourceCategoryMetadataItem).\
                 filter_by(category_id=code)
        result = result + [x for x in fields]

    return result


def _validate_category_metadata(resource, current=None):

    errors = {}
    category = resource.get('category', None)
    if category is None:
        _add_error(errors, 'category', 'Category not chosen.')

    metadata_fields = get_required_metadata_fields(category)

    for entry in metadata_fields:
        field_value = resource.get(entry.title, None)
        if field_value is None or field_value == u'':
            _add_error(errors, entry.title, 'Field should not be empty.')
            continue

        _validator_fun(entry.datatype)(category,
                                       entry.title,
                                       field_value,
                                       errors)

    if len(errors) > 0:
        if current:
            # For some reason, the full link disappears in the resource object,
            # which can lead to a cycle of errors.  We reinstate the full link
            # here for now.  @@ Is there a better way?
            # resource['url'] = current['url']
            pass

        raise ValidationError(errors, error_summary=_make_summary(errors))


def _make_summary(errors):
    return {key: "There was an error with category-specific field  '{0}'".
            format(key)
            for key in errors}


class CdsMetadataResourcesPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IResourceController)

    def before_create(self, context, resource):
        u'''
        Extensions will receive this before a resource is created.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resource: An object representing the resource to be added
            to the dataset (the one that is about to be created).
        :type resource: dictionary
        '''
        _validate_category_metadata(resource)
        pass

    def after_create(self, context, resource):
        u'''
        Extensions will receive this after a resource is created.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resource: An object representing the latest resource added
            to the dataset (the one that was just created). A key in the
            resource dictionary worth mentioning is ``url_type`` which is
            set to ``upload`` when the resource file is uploaded instead
            of linked.
        :type resource: dictionary
        '''
        pass

    def before_update(self, context, current, resource):
        u'''
        Extensions will receive this before a resource is updated.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param current: The current resource which is about to be updated
        :type current: dictionary
        :param resource: An object representing the updated resource which
            will replace the ``current`` one.
        :type resource: dictionary
        '''
        _validate_category_metadata(resource, current)
        pass


    def after_update(self, context, resource):
        u'''
        Extensions will receive this after a resource is updated.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resource: An object representing the updated resource in
            the dataset (the one that was just updated). As with
            ``after_create``, a noteworthy key in the resource dictionary
            ``url_type`` which is set to ``upload`` when the resource file
            is uploaded instead of linked.
        :type resource: dictionary
        '''
        pass

    def before_delete(self, context, resource, resources):
        u'''
        Extensions will receive this before a previously created resource is
        deleted.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resource: An object representing the resource that is about
            to be deleted. This is a dictionary with one key: ``id`` which
            holds the id ``string`` of the resource that should be deleted.
        :type resource: dictionary
        :param resources: The list of resources from which the resource will
            be deleted (including the resource to be deleted if it existed
            in the package).
        :type resources: list
        '''
        pass

    def after_delete(self, context, resources):
        u'''
        Extensions will receive this after a previously created resource is
        deleted.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resources: A list of objects representing the remaining
            resources after a resource has been removed.
        :type resource: list
        '''
        pass

    def before_show(self, resource_dict):
        u'''
        Extensions will receive the validated data dict before the resource
        is ready for display.

        Be aware that this method is not only called for UI display, but also
        in other methods like when a resource is deleted because showing a
        package is used to get access to the resources in a package.
        '''
        pass


