from typing import Literal
from xml.etree import ElementTree as ET

from pyjabber import AppConfig
from pyjabber.stanzas.IQ import IQ


def iq_skeleton(element: ET.Element, disco_type: Literal['info', 'items']):
    iq_res = IQ(
        type_=IQ.TYPE.RESULT,
        id_=element.get('id'),
        from_=element.get('to'),
        to=element.get('from')
    )
    return iq_res, ET.SubElement(
        iq_res, f'{{http://jabber.org/protocol/disco#{disco_type}}}query'
    )


def server_info(element: ET.Element):
    iq_res, query = iq_skeleton(element, 'info')
    ET.SubElement(
        query,
        '{http://jabber.org/protocol/disco#info}identity',
        attrib={'category': 'protocols', 'type': 'im', 'name': 'PyJabber Server'})

    for feature in AppConfig.app_config.plugins:
        ET.SubElement(
            query,
            '{http://jabber.org/protocol/disco#info}feature',
            attrib={'var': feature}
        )

    return ET.tostring(iq_res)


def server_items(element: ET.Element):
    iq_res, query = iq_skeleton(element, 'items')
    ET.SubElement(
        query,
        '{http://jabber.org/protocol/disco#items}identity',
        attrib={'category': 'protocols', 'type': 'im', 'name': 'PyJabber Server'})

    for key, info in AppConfig.app_config.items.items():
        jid = key.replace('$', AppConfig.app_config.host) if '$' in key else key
        ET.SubElement(
            query,
            '{http://jabber.org/protocol/disco#items}item',
            attrib={'jid': jid, 'name': info['name']}
        )

    return ET.tostring(iq_res)
