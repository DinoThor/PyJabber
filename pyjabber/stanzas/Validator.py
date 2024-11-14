from typing import Dict

from pyjabber.utils import Singleton
from xml.etree import ElementTree as ET
from pyjabber.utils import ClarkNotation as CN
import xmlschema
import os

DIR_PATH = os.path.dirname(os.path.realpath(__file__))


class NotSchemaFoundException(Exception):
    pass


class Validator(metaclass=Singleton):
    def __init__(self):
        self._schemas: Dict[str, xmlschema.XMLSchema] = {
            'jabber:x:data': xmlschema.XMLSchema(os.path.join(DIR_PATH, 'schemas', 'x-data.xsd'))
        }

    def validate(self, element: ET.Element):
        ns, _ = CN.deglose(element.tag)
        try:
            return self._schemas[ns].is_valid(element)
        except KeyError:
            raise NotSchemaFoundException('Missing schema file in server for given namespace')
