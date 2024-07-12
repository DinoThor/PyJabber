from enum import Enum
from typing import Dict
from xml.etree import ElementTree as ET

from pyjabber.features.FeatureInterface import FeatureInterface


class Signal(Enum):
    RESET = 0
    DONE = 1


class TLS(FeatureInterface):
    def __init__(self):
        pass

    def feed(self, element: ET.Element):
        pass


class StartTLSFeature(ET.Element):
    def __init__(
        self,
        tag: str = "starttls",
        attrib: Dict[str, str] = {
            "xmlns": "urn:ietf:params:xml:ns:xmpp-tls"
        },
        required: bool = True,
            **extra: str) -> None:
        super().__init__(tag, attrib, **extra)

        if required:
            self.append(ET.Element("required"))

    @staticmethod
    def proceed_response() -> bytes:
        elem = ET.Element(
            "proceed", attrib={
                "xmlns": "urn:ietf:params:xml:ns:xmpp-tls"})
        return ET.tostring(elem)
