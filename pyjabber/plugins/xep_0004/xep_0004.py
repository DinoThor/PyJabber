from enum import Enum
from loguru import logger
from xml.etree import ElementTree as ET

from pyjabber.stanzas.Validator import Validator, NotSchemaFoundException


class FormType(Enum):
    FORM = 'form'
    SUBMIT = 'submit'
    CANCEL = 'cancel'
    RESULT = 'result'


class FieldTypes(Enum):
    BOOLEAN = 'boolean'
    FIXED = 'fixed'
    HIDDEN = 'hidden'
    JID_MULTI = 'jid-multi'
    JID_SINGLE = 'jid-single'
    LIST_MULTI = 'list-multi'
    LIST_SINGLE = 'list-single'
    TEXT_MULTI = 'text-multi'
    TEXT_PRIVATE = 'text-private'
    TEXT_SINGLE = 'text-single'


class DataForms:
    def __init__(self):
        self._xmlns = 'jabber:x:data'
        self._validator = Validator()

    def validate_form(self, element: ET.Element):
        try:
            self._validator.validate(element)
        except NotSchemaFoundException:
            logger.error('INTERNAL ERROR: Not schema found for form validation')

    def parse_form(self, element: ET.Element):
        pass

    def generate_form(self):
        pass
