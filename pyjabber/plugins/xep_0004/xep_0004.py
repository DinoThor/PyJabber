from enum import Enum
from typing import List

from xml.etree import ElementTree as ET

from pyjabber.plugins.xep_0004.field import FieldRequest, FieldResponse, FieldTypes
from pyjabber.utils import ClarkNotation as CN
from pyjabber.stanzas.error import StanzaError as SE


class MissingDataForms(Exception):
    """
    No dataforms founded in a stanza, when it was expected
    """
    pass


class FormType(Enum):
    FORM = 'form'
    SUBMIT = 'submit'
    CANCEL = 'cancel'
    RESULT = 'result'


def parse_form(element: ET.Element):
    """
    If a proper dataforms is passes, it returns a list of field
    submitted by the client
    @param element:
    @return: List of dicts in format {type, var, values[]}
    """
    data = None
    try:
        """
        Supposing element is an IQ stanza, it should be in a second-level child
        """
        forms = element[0][0]
        ns, tag = CN.deglose(forms.tag)
        if tag != 'x' or ns != 'jabber:x:data':
            raise MissingDataForms
        data = forms
    except (KeyError, MissingDataForms):
        """
        Supposing element is an Message stanza, it should be in a first-level child
        """
        try:
            forms = element[0]
            ns, tag = CN.deglose(forms.tag)
            if tag != 'x' or ns != 'jabber:x:data':
                raise MissingDataForms
            data = forms
        except (KeyError, MissingDataForms):
            return SE.bad_request()

    field_list = data.findall('{jabber:x:data}field')
    try:
        field_list = [
            FieldResponse(
                field_type=FieldTypes.from_value(f.attrib.get('type')),
                var=f.attrib.get('var'),
                values=[v.text for v in f.findall('{jabber:x:data}value')]
            ) for f in field_list]
    except KeyError:
        return SE.bad_request()

    return field_list


def generate_form(form_type: FormType, title: str = None, instructions: str = None, fields: List[FieldRequest] = None) -> ET.Element:
    form_res = ET.Element('x', attrib={'xmlns': 'jabber:x:data', 'type': form_type.value})

    if form_type == FormType.CANCEL.value:
        return form_res

    if title:
        ET.SubElement(form_res, 'title').text = title

    if instructions:
        ET.SubElement(form_res, 'instructions').text = instructions

    for f in fields:
        field = ET.Element('field', attrib={
            'type': f.type.value,
            'var': f.var
        })

        if f.label:
            field.attrib['label'] = f.label

        for v in f.values:
            value = ET.Element('value')
            value.text = v
            field.append(value)

        if f.options:
            for o in f.options:
                option = ET.Element('option')
                option.text = o
                field.append(option)

        if f.desc:
            desc = ET.Element('desc')
            desc.text = f.desc
            field.append(desc)

        form_res.append(field)

    return form_res


def generate_form_multi_res():
    pass
