from typing import Literal
from yaml import load, Loader
from xml.etree import ElementTree as ET

from pyjabber.metadata import Metadata

from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.plugins.xep_0060.xep_0060 import PubSub
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ


def iq_skeleton(element: ET.Element, disco_type: Literal['info', 'items']):
    iq_res = IQ(
        type=IQ.TYPE.RESULT.value,
        id=element.get('id'),
        from_=element.get('to'),
        to=element.get('from')
    )
    return iq_res, ET.SubElement(iq_res, 'query', attrib={'xmlns': f'http://jabber.org/protocol/disco#{disco_type}'})


class Disco(Plugin):
    def __init__(cls, jid: str):
        cls.jid = jid
        cls._handlers = {
            "info": cls.handle_info,
            "items": cls.handle_items
        }
        cls._host = Metadata().host
        cls._config_path = Metadata().config_path
        cls._items = list(load(open(cls._config_path), Loader=Loader).get('items'))

        # Search if any item has the substring pubsub, and replace the placeholder
        # with the server's host of the current session
        # A none result means the pubsub feature is disable
        cls._pubsub_jid = next((s for s in list(cls._items) if 'pubsub' in s), None)
        if cls._pubsub_jid:
            cls._pubsub_jid = cls._pubsub_jid.replace('$', cls._host)

        cls._pubsub = PubSub()

    def feed(self, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        if element.find('{http://jabber.org/protocol/disco#info}query') is not None:
            return self._handlers['info'](element)
        elif element.find('{http://jabber.org/protocol/disco#items}query') is not None:
            return self._handlers['items'](element)
        else:
            pass

    def handle_info(self, element: ET.Element) -> object:
        to = element.attrib.get('to')

        # Server info
        if to == self._host or to is None:
            return self.server_info(element)

        # Pubsub info
        if self._pubsub_jid and to == self._pubsub_jid:
            iq_res, query = iq_skeleton(element, 'info')
            ET.SubElement(
                query,
                'identity',
                attrib={'category': 'pubsub', 'type': 'service'}
            )
            ET.SubElement(query, 'feature', attrib={'var': 'http://jabber.org/protocol/pubsub'})
            return ET.tostring(iq_res)

    def handle_items(self, element: ET.Element):
        to = element.attrib.get('to')

        # Server items
        if to == self._host or to is None:
            return self.server_items(element)

        # Pubsub items
        if self._pubsub_jid and to == self._pubsub_jid:
            return self._pubsub.discover_items(element)


    def server_info(self, element: ET.Element):
        plugins = load(open(self._config_path), Loader=Loader)['plugins']
        iq_res, query = iq_skeleton(element, 'info')
        ET.SubElement(
            query,
            'identity',
            attrib={'category': 'server', 'type': 'im', 'name': 'PyJabber Server'})

        for feature in plugins:
            ET.SubElement(query, 'feature', attrib={'var': feature})

        return ET.tostring(iq_res)

    def server_items(self, element: ET.Element):
        items = load(open(self._config_path), Loader=Loader)['items']
        iq_res, query = iq_skeleton(element, 'items')
        ET.SubElement(
            query,
            'identity',
            attrib={'category': 'server', 'type': 'im', 'name': 'PyJabber Server'})

        for i in items:
            [*keys], [*values] = zip(*i.items())
            if '$' in values[0][0]:
                jid = values[0][0].replace('$', Metadata().host)
            else:
                jid = values[0][0]

            ET.SubElement(query, 'item', attrib={'jid': jid, 'name': keys[0]})

        return ET.tostring(iq_res)

    def pubsub_info(self, element: ET.Element):
        pass
