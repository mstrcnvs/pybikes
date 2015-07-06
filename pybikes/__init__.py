# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

"""PyBikes
PyBikes is a parsing library to extract bike sharing information from multiple
sources. It contains multiple classes to handle this sort of information,
and is not a class itself. The idea is to be able to call it like:

from pybikes import BicingShareSystem, BicingStation

bicing = new BicingShareSystem() <- Returns BicingShareSystem
print "%s: %s" % ("Bicing City is", bicing.meta.city)
stations = bicing.get_stations() <- Returns Array[BicingStation]

"""
__author__ = "eskerda (eskerda@gmail.com)"
__version__ = "2.0"
__copyright__ = "Copyright (c) 2010-2012 eskerda"
__license__ = "AGPL"

import re
import json
from pkg_resources import resource_string, resource_listdir

try:
    from itertools import imap as map  # Python 2
except ImportError:
    pass

try:
    text_type = unicode  # Python 2
except NameError:
    text_type = str  # Python 3

try:
    iteritems = dict.iteritems  # Python 2
except AttributeError:
    def iteritems(d):  # Python 3
        return iter(d.items())

from pybikes.exceptions import BikeShareSystemNotFound

# Top class shortcuts
from pybikes.base import BikeShareSystem, BikeShareStation
from pybikes import utils
from pybikes import contrib


def get_data(schema):
    name = re.sub(r'\.json$', '', schema)
    data = resource_string(__name__, 'data/{}.json'.format(name))
    return json.loads(data.decode('utf-8'))


def get_all_data():
    return resource_listdir(__name__, 'data')


def get_schemas():
    return map(
        lambda name: re.sub(r'\.json$', '', name),
        get_all_data()
    )

def _uniclass_extractor(data):
    for i in data['instances']:
        yield (data['class'], i)


def _multiclass_extractor(data):
    for k, v in iteritems(data['class']):
        for i in data['class'][k]['instances']:
            yield (k, i)


def get_instances(schema=None):
    if not schema:
        schemas = get_schemas()
    else:
        schemas = [schema]
    for schema in schemas:
        data = get_data(schema)
        if isinstance(data['class'], text_type):
            extractor = _uniclass_extractor
        elif isinstance(data['class'], dict):
            extractor = _multiclass_extractor
        else:
            raise Exception('Malformed data file {}'.format(schema))
        for cname, instance in extractor(data):
            yield (cname, instance)


def get_system_cls(schema, cname):
    module = __import__('%s.%s' % (__name__, schema))
    sysm = getattr(module, schema)
    syscls = getattr(sysm, cname)
    return syscls


def get_instance(schema, tag):
    cname, instance = next(
        ((c, i) for (c, i) in get_instances(schema) if i['tag'] == tag),
        (None, None)
    )
    if not instance:
        msg = 'System %s not found in schema %s' % (tag, schema)
        raise BikeShareSystemNotFound(msg)
    syscls = get_system_cls(schema, cname)
    return (syscls, instance)


def find_system(tag):
    datas = map(get_data, get_all_data())
    for data in datas:
        schema = data['system']
        try:
            syscls, instance = get_instance(schema, tag)
        except BikeShareSystemNotFound:
            continue
        return (syscls, instance)
    raise BikeShareSystemNotFound('System %s not found' % tag)


def get(tag, key=None):
    syscls, system = find_system(tag)
    if syscls.authed and not key:
        raise Exception('System %s needs a key to work' % syscls.__name__)
    if syscls.authed:
        system['key'] = key
    return syscls(**system)


# These are here for retrocompatibility purposes
def getBikeShareSystem(system, tag, key=None):
    return get(tag, key)


def getDataFile(schema):
    return get_data(schema)


def getDataFiles():
    return get_all_data()
