from typing import Literal
from yaml import load, Loader
from xml.etree import ElementTree as ET

from pyjabber.metadata import Metadata

from pyjabber.plugins.xep_0060.xep_0060 import PubSub, NodeAttrib
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton


def iq_skeleton(element: ET.Element, disco_type: Literal['info', 'items']):
    iq_res = IQ(
        type=IQ.TYPE.RESULT.value,
        id=element.get('id'),
        from_=element.get('to'),
        to=element.get('from')
    )
    return iq_res, ET.SubElement(iq_res, 'query', attrib={'xmlns': f'http://jabber.org/protocol/disco#{disco_type}'})


class Disco(metaclass=Singleton):
    def __init__(self):
        self._handlers = {
            "info": self.handle_info,
            "items": self.handle_items
        }
        self._host = Metadata().host
        self._config_path = Metadata().config_path
        self._items = list(load(open(self._config_path), Loader=Loader).get('items'))

        # Search if any item has the substring pubsub, and replace the placeholder
        # with the server's host of the current session
        # A none result means the pubsub feature is disable
        self._pubsub_jid = next((s for s in list(self._items) if 'pubsub' in s), None)
        if self._pubsub_jid:
            self._pubsub_jid = domain=self._pubsub_jid.replace('$', self._host)
            self._pubsub = PubSub()

    def feed(self, jid: str, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        if element.find('{http://jabber.org/protocol/disco#info}query') is not None:
            return self._handlers['info'](jid, element)
        elif element.find('{http://jabber.org/protocol/disco#items}query') is not None:
            return self._handlers['items'](jid, element)
        else:
            pass

    def handle_info(self, jid: str, element: ET.Element):
        to = element.attrib.get('to')
        if to is not None:
            to = JID(to)
        else:
            return self.server_info(element)

        if to.domain == self._host:
            return self.server_info(element)

        # Pubsub info
        if self._pubsub_jid and to == self._pubsub_jid:
            iq_res, query_res = iq_skeleton(element, 'info')

            node = self._pubsub.discover_info(element)
            if node:
                ET.SubElement(
                    query_res,
                    'identity',
                    attrib={'category': 'pubsub', 'type': node[-1]}
                )
                return ET.tostring(iq_res)

            ET.SubElement(
                query_res,
                'identity',
                attrib={'category': 'pubsub', 'type': 'service'}
            )
            ET.SubElement(query_res, 'feature', attrib={'var': 'http://jabber.org/protocol/pubsub'})
            return ET.tostring(iq_res)

    def handle_items(self, jid: str, element: ET.Element):
        to = element.attrib.get('to')

        # Server items
        if to == self._host or to is None:
            return self.server_items(element)

        # Pubsub items
        if self._pubsub_jid and to == self._pubsub_jid:
            nodes = self._pubsub.discover_items(element)
            iq_res, query = iq_skeleton(element, 'items')
            for node in nodes:
                ET.SubElement(query, 'item', attrib={'jid': self._pubsub_jid, 'node': node[NodeAttrib.NODE.value], 'name': node[NodeAttrib.NAME.value]})
            return ET.tostring(iq_res)

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
