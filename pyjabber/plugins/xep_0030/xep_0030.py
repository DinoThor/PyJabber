from typing import Literal, Dict, Callable
from xml.etree import ElementTree as ET

from pyjabber import metadata
from pyjabber.plugins.xep_0004.field import FieldRequest, FieldTypes
from pyjabber.plugins.xep_0060.xep_0060 import PubSub, NodeAttrib
from pyjabber.plugins.xep_0004.xep_0004 import generate_form, FormType
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton


def iq_skeleton(element: ET.Element, disco_type: Literal['info', 'items']):
    iq_res = IQ(
        type_=IQ.TYPE.RESULT,
        id_=element.get('id'),
        from_=element.get('to'),
        to=element.get('from')
    )
    return iq_res, ET.SubElement(iq_res, f'{{http://jabber.org/protocol/disco#{disco_type}}}query')


class Disco(metaclass=Singleton):
    __slots__ = ('_handlers', '_config_path', '_pubsub', '_pubsub_jid', '_0363_jid', '_0363_max_size')

    def __init__(self):
        self._handlers: Dict[str, Callable[[JID, ET.Element], bytes]] = {
            "info": self.handle_info,
            "items": self.handle_items
        }
        self._config_path: str = metadata.CONFIG_PATH

        if 'http://jabber.org/protocol/pubsub' in metadata.PLUGINS:
            self._pubsub_jid = next((s for s in metadata.ITEMS if 'pubsub' in s), None)
            self._pubsub_jid = self._pubsub_jid.replace('$', metadata.HOST)
            self._pubsub = PubSub()

        if 'urn:xmpp:http:upload:0' in metadata.PLUGINS:
            self._0363_jid = next((s for s in metadata.ITEMS if 'upload' in s), None)
            self._0363_max_size = metadata.ITEMS[self._0363_jid]["extra"]["max-size"]
            self._0363_jid = self._0363_jid.replace('$', metadata.HOST)


    def feed(self, jid: JID, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        if element.find('{http://jabber.org/protocol/disco#info}query') is not None:
            return self._handlers['info'](jid, element)

        elif element.find('{http://jabber.org/protocol/disco#items}query') is not None:
            return self._handlers['items'](jid, element)

    def handle_info(self, _, element: ET.Element):
        to = element.attrib.get('to')

        # Pubsub info
        if self._pubsub_jid and to == self._pubsub_jid:
            iq_res, query_res = iq_skeleton(element, 'info')
            query = element.find('{http://jabber.org/protocol/disco#info}query')
            node = query.attrib.get('node')

            if node:
                info = self._pubsub.discover_info(node)

                ET.SubElement(
                    query_res,
                    '{http://jabber.org/protocol/disco#info}identity',
                    attrib={'category': 'pubsub', 'type': info[-1]}
                )
                return ET.tostring(iq_res)

            ET.SubElement(
                query_res,
                '{http://jabber.org/protocol/disco#info}identity',
                attrib={'category': 'pubsub', 'type': 'service'}
            )
            ET.SubElement(
                query_res,
                '{http://jabber.org/protocol/disco#info}feature',
                attrib={'var': 'http://jabber.org/protocol/pubsub'}
            )

            return ET.tostring(iq_res)

        # XEP 0363 (HTTP File Upload) info
        elif self._0363_jid and to == self._0363_jid:
            iq_res, query_res = iq_skeleton(element, 'info')
            ET.SubElement(
                query_res,
                '{http://jabber.org/protocol/disco#info}identity',
                attrib={'category': 'store', 'type': 'file', 'name': 'HTTP File Upload'}
            )
            ET.SubElement(
                query_res,
                '{http://jabber.org/protocol/disco#info}feature',
                attrib={'var': 'urn:xmpp:http:upload:0'}
            )

            dataform = generate_form(
                form_type=FormType.RESULT,
                fields=[
                    FieldRequest(var='FORM_TYPE', field_type=FieldTypes.HIDDEN, values=['urn:xmpp:http:upload:0']),
                    FieldRequest(var='max-file-size', values=[str(self._0363_max_size)])
                ]
            )
            query_res.append(dataform)

            return ET.tostring(iq_res)

        else:
            return self.server_info(element)

    def handle_items(self, _, element: ET.Element):
        to = element.attrib.get('to')

        if self._pubsub_jid and to == self._pubsub_jid:
            # query = element.find('{http://jabber.org/protocol/disco#items}query')
            # node = query.attrib.get('node')
            items = self._pubsub.discover_items()

            iq_res, query = iq_skeleton(element, 'items')
            for n in items:
                ET.SubElement(
                    query,
                    '{http://jabber.org/protocol/disco#items}item',
                    attrib={
                        'jid': self._pubsub_jid,
                        'node': n[NodeAttrib.NODE.value],
                        'name': n[NodeAttrib.NAME.value]
                })
            return ET.tostring(iq_res)

        else:
            return self.server_items(element)

    @staticmethod
    def server_info(element: ET.Element):
        iq_res, query = iq_skeleton(element, 'info')
        ET.SubElement(
            query,
            '{http://jabber.org/protocol/disco#info}identity',
            attrib={'category': 'server', 'type': 'im', 'name': 'PyJabber Server'})

        for feature in metadata.PLUGINS:
            ET.SubElement(query, '{http://jabber.org/protocol/disco#info}feature', attrib={'var': feature})

        return ET.tostring(iq_res)

    @staticmethod
    def server_items(element: ET.Element):
        iq_res, query = iq_skeleton(element, 'items')
        ET.SubElement(
            query,
            '{http://jabber.org/protocol/disco#items}identity',
            attrib={'category': 'server', 'type': 'im', 'name': 'PyJabber Server'})

        for key, info in metadata.ITEMS.items():
            jid = key.replace('$', metadata.HOST) if '$' in key else key
            ET.SubElement(query, '{http://jabber.org/protocol/disco#items}item', attrib={'jid': jid, 'name': info['name']})

        return ET.tostring(iq_res)
