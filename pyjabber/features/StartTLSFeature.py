from enum import Enum
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from pyjabber.features.FeatureInterface import FeatureInterface
import xml.etree.ElementTree as ET


# # TCP Connection opened
#         if self._stage == Stage.CONNECTED:
#             self._streamFeature.reset()
#             self._streamFeature.register(StartTLSFeature())
#             self._buffer.write(self._streamFeature.tobytes())
            
#             self._stage = Stage.OPENED

#         # TLS feature sended
#         elif self._stage == Stage.OPENED:
#             if "starttls" in elem.tag:
#                 self._buffer.write(StartTLSFeature().proceedResponse())
#                 self._starttls()
#                 self._stage = Stage.SSL
#                 return Signal.RESET


class Signal(Enum):
    RESET   = 0
    DONE    = 1


class TLS(FeatureInterface):
    def __init__(self):
        pass

    def feed(element: ET.Element):
        pass


class StartTLSFeature(ElementTree.Element):
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
            self.append(Element("required"))

    def proceedResponse(self) -> bytes:
        elem = Element("proceed", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-tls"})
        return ElementTree.tostring(elem)
