import json
from json import JSONEncoder
import pdb

_schemafile = 'utils/metadata_schema.json'

classdict = {}

with open(_schemafile) as f:
    schema = json.load(f)


class Sigma2Exception(BaseException):
    pass


class Sigma2JSONEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


def _initfun(self, pdict, **kwargs):

    # set default properties
    for k, v in pdict.items():
        default_val = [] if v.get('type') == 'array' else None
        setattr(self, k, default_val)

    # add-in user-specfied arguments
    for k, v in kwargs.items():
        if hasattr(self, k):
            if getattr(self, k) == list:
                setattr(self, k, v if type(v) == list else [v])
            else:
                setattr(self, k, v)
        else:
            raise Sigma2Exception('Tried to set unknown attribute.')


def _initfunwrap(pdict):
    return lambda self, **kwargs: _initfun(self, pdict, **kwargs)


def _make_typemap(pdict):
    common_types = {'string': str, 'array': list, 'boolean': bool}

    result = {}
    for k, v in pdict.items():
        T = v.get('type')  # could be None if field does not exist
        is_array = T == 'array'
        valid_types = None  # We will determine this below
        if T:
            if is_array:
                assert(v.get('items'))
                valid_types = [v['items']['$ref'].split('/')[-1]]
            else:
                valid_types = [common_types[T]]  # a single valid type

        else:  # the field 'type' was not present in the 'v' dict.
            if v.get('$ref'):
                valid_types = [v['$ref'].split('/')[-1]]
            else:
                assert(v.get('anyOf'))  # in that case; 'anyOf' key should be there
                valid_types = [x['$ref'].split('/')[-1] for x in v['anyOf']]

        result[k] = (valid_types, is_array)

    return result


class Sigma2Baseclass:

    _required = []  # list over required fields
    _typemap = {}  # map fields to expected types

    def missingRequirements(self):
        result = []
        for field in self._required:
            if not hasattr(self, field):
                raise Sigma2Exception('Required attribute does not exist.')
            elif not getattr(self, field):
                result.append(field)
        return result

    def typeMismatches(self):
        mismatches = []
        for k, v in self._typemap.items():
            pval = getattr(self, k)
            if pval is None:
                continue  # value not set anyway, so no reason to check type

            elif v[1]:  # the value sould be an array

                if not type(pval) == list:
                    mismatches.append((k, type(pval), [v[0]]))
                    continue
                # check list items
                for item in pval:
                    if type(item) not in v[0] and \
                       type(item).__name__ not in v[0]:
                        mismatches.append((k, [type(pval)], [v[0]]))
                        break

            else:  # should not be an array, match directly
                if type(pval) not in v[0] and \
                   type(pval).__name__ not in v[0]:
                    mismatches.append((k, type(pval), v[0]))

        return mismatches

    def metadataFields(self):
        return list(set(dir(self)) - set(dir(Sigma2Baseclass)))

    def invalidations(self):
        missing = []
        mismatches = []

        # check that all required fields are filled in, and that all values are
        # of legal types
        if self.missingRequirements():
            missing = [(type(self), x) for x in self.missingRequirements()]
        if self.typeMismatches():
            mismatches = [(type(self), x) for x in self.typeMismatches()]

        # recursively checking attributes in same manner
        for field in set(dir(self)) - set(dir(Sigma2Baseclass)):
            content = getattr(self, field)
            if not type(content) == list:
                content = [content]
            for item in content:
                if isinstance(item, Sigma2Baseclass):
                    item_miss, item_mismatch = item.invalidations()
                    missing.extend(item_miss)
                    mismatches.extend(item_mismatch)

        return missing, mismatches

    def isValid(self):
        missing, mismatches = self.invalidations()
        return not missing and not mismatches

    def toJSON(self):
        return Sigma2JSONEncoder().encode(self)


# create the main class, and all other classes
classinfo = {'dataset': schema, **schema['definitions']}
for cname, cvals in classinfo.items():
    classdict[cvals['title']] = \
        type(cvals['title'],
             (Sigma2Baseclass,),
             {'__doc__': cvals['description'],
              '__init__': _initfunwrap(cvals['properties']),
              '_typemap': _make_typemap(cvals['properties']),
              '_required': cvals['required']})
