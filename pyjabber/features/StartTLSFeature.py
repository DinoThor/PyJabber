from enum import Enum
from typing import Dict
from xml.etree import ElementTree as ET


class Signal(Enum):
    RESET = 0
    DONE = 1


def proceed_response() -> bytes:
    elem = ET.Element(
        "proceed", attrib={
            "xmlns": "urn:ietf:params:xml:ns:xmpp-tls"})
    return ET.tostring(elem)


class StartTLSFeature(ET.Element):
    def __init__(
        self,
        tag: str = "starttls",
        attrib = None,
        required: bool = True,
            **extra: str) -> None:

        default_atrrib = {
            "xmlns": "urn:ietf:params:xml:ns:xmpp-tls"
        }

        super().__init__(tag, attrib or default_atrrib, **extra)

        if required:
            self.append(ET.Element("required"))
