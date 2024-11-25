from xml.etree import ElementTree as ET

from pyjabber.plugins.xep_0004.xep_0004 import parse_form

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
    values = parse_form(form_element)
