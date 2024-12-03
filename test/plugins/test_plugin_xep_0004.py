from xml.etree import ElementTree as ET

from pyjabber.plugins.xep_0004.field import FieldTypes, FieldRequest
from pyjabber.plugins.xep_0004.xep_0004 import parse_form, FormType, generate_form

"""
<message>
    <x xmlns='jabber:x:data' type='result'>
      <field type='hidden' var='FORM_TYPE'>
        <value>jabber:bot</value>
      </field>
      <field type='text-single' var='botname'>
        <value>The Jabber Google Bot</value>
      </field>
      <field type='boolean' var='public'>
        <value>0</value>
      </field>
      <field type='text-private' var='password'>
        <value>v3r0na</value>
      </field>
      <field type='list-multi' var='features'>
        <value>news</value>
        <value>search</value>
      </field>
      <field type='list-single' var='maxsubs'>
        <value>50</value>
      </field>
      <field type='jid-multi' var='invitelist'>
        <value>juliet@capulet.com</value>
        <value>benvolio@montague.net</value>
      </field>
    </x>
</message>
"""

form = "<message><x xmlns='jabber:x:data' type='result'><field type='hidden' var='FORM_TYPE'><value>jabber:bot</value></field><field type='text-single' var='botname'><value>The Jabber Google Bot</value></field><field type='boolean' var='public'><value>0</value></field><field type='text-private' var='password'><value>v3r0na</value></field><field type='list-multi' var='features'><value>news</value><value>search</value></field><field type='list-single' var='maxsubs'><value>50</value></field><field type='jid-multi' var='invitelist'><value>juliet@capulet.com</value><value>benvolio@montague.net</value></field></x></message>"
form_element = ET.fromstring(form)


def test_parse_form():
    form_parsed = parse_form(form_element)
    assert form_parsed[0].type == FieldTypes.HIDDEN
    assert form_parsed[0].var == 'FORM_TYPE'
    assert form_parsed[0].values[0] == 'jabber:bot'
    assert form_parsed[1].type == FieldTypes.TEXT_SINGLE
    assert form_parsed[1].var == 'botname'
    assert form_parsed[1].values[0] == 'The Jabber Google Bot'
    assert form_parsed[-1].type == FieldTypes.JID_MULTI
    assert form_parsed[-1].var == 'invitelist'
    assert form_parsed[-1].values[0] == 'juliet@capulet.com'
    assert form_parsed[-1].values[1] == 'benvolio@montague.net'

"""
<x xmlns='jabber:x:data' type='result'>
  <field type='hidden' var='FORM_TYPE'>
    <value>jabber:bot</value>
  </field>
  <field type='text-single' var='botname' label='The bot name'>
    <value>Google Bot</value>
  </field>
  <field type='jid-multi' var='invitelist'>
    <value>juliet@capulet.com</value>
    <value>benvolio@montague.net</value>
  </field>
</x>
"""

def test_generate_form():
    form = generate_form(
        form_type=FormType.FORM,
        title='Form Test',
        instructions='Fill this form to test it',
        fields=[
            FieldRequest(
                field_type=FieldTypes.HIDDEN,
                var='FORM_TYPE',
                values=['jabber:bot']
            ),
            FieldRequest(
                field_type=FieldTypes.TEXT_SINGLE,
                var='botname',
                label='The bot name',
                values=['Google Bot']
            ),
            FieldRequest(
                field_type=FieldTypes.JID_MULTI,
                var='invitelist',
                values=['juliet@capulet.com', 'benvolio@montague.net']
            )
        ]
    )

    assert form.tag == 'x'
    assert form.attrib.get('xmlns') == 'jabber:x:data'
    assert form.attrib.get('type') == FormType.FORM.value
    fields = form.findall('field')
    assert fields[0].tag == 'field'
    assert fields[0].attrib.get('type') == FieldTypes.HIDDEN.value
    assert fields[0].attrib.get('var') == 'FORM_TYPE'
    assert fields[0].findall('value')[0].text == 'jabber:bot'
