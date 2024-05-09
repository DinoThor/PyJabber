from enum import Enum
from xml.etree import ElementTree as ET

from pyjabber.features.FeatureInterface import FeatureInterface


class Signal(Enum):
    RESET   = 0
    DONE    = 1


class TLS(FeatureInterface):
    def __init__(self):
        pass

    def feed(element: ET.Element):
        pass


class StartTLSFeature(ET.Element):
    def __init__(
            self, 
            tag     : str = "starttls", 
            attrib  : dict[str, str] = {
                "xmlns" : "urn:ietf:params:xml:ns:xmpp-tls"
            },
            required: bool = True,
            **extra : str) -> None:

        super().__init__(tag, attrib, **extra)

        if required: 
            self.append(ET.Element("required"))

    def proceedResponse(self) -> bytes:
        elem = ET.Element("proceed", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-tls"})
        return ET.tostring(elem)
