from yaml import load, Loader

from xml.etree import ElementTree as ET

from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.config.config import CONFIG_FILE
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ


class Disco(Plugin):
    def __init__(self):
        self._handlers = {
            "info": self.handle_info,
            "items": self.handle_items
        }

    def feed(self, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        if element.find('{http://jabber.org/protocol/disco#info}query') is not None:
            return self._handlers['info'](element)
        elif element.find('{http://jabber.org/protocol/disco#items}query') is not None:
            return self._handlers['info'](element)
        else:
            pass

    def handle_info(self, element: ET.Element):
        # Server info
        plugins = load(open(CONFIG_FILE), Loader=Loader)['plugins']
        if element.attrib['to'] == 'localhost':
            element_id = element.get('id')
            element_to = element.attrib.get('to')
            element_from = element.attrib.get('from')

            iq_res = IQ(type=IQ.TYPE.RESULT.value, id=element_id, from_=element_to, to=element_from)
            query = ET.SubElement(iq_res, 'query', attrib={'xmlns': 'http://jabber.org/protocol/disco#items'})
            ET.SubElement(
                query,
                'identity',
                attrib={'category': 'server', 'type': 'im', 'name': 'PyJabber Server'})

            for feature in plugins:
                ET.SubElement(query, 'feature', attrib={'var': feature})

            return ET.tostring(iq_res)

    def handle_items(self, element: ET.Element):
        pass
