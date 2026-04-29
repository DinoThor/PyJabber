from typing import Tuple
from uuid import uuid4
from xml.etree import ElementTree as ET

from pyjabber import AppConfig
from pyjabber.stanzas.IQ import IQ


def success_response(element: ET.Element, owner: bool = False) -> Tuple[IQ, ET.Element]:
    iq_res = IQ(
        type_=IQ.TYPE.RESULT,
        from_=AppConfig.app_config.host,
        id_=element.attrib.get("id") or str(uuid4()),
    )
    if owner:
        xmlns = "http://jabber.org/protocol/pubsub#owner"
    else:
        xmlns = "http://jabber.org/protocol/pubsub"

    pubsub = ET.SubElement(iq_res, f"{{{xmlns}}}pubsub")
    return iq_res, pubsub
