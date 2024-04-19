from enum import Enum
from xml.etree import ElementTree
from xml.etree.ElementTree import Element


class mechanismEnum(Enum):
    PLAIN       = "PLAIN"
    SCRAM_SHA_1 = "SCRAM-SHA-1"

class SASLFeature(ElementTree.Element):
    
    def __init__(
            self, 
            tag         : str = "mechanisms", 
            attrib      : dict[str, str] = {
                "xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"
            },
            mechanism   : list[mechanismEnum] = [mechanismEnum.PLAIN],
            **extra : str) -> None:
        super().__init__(tag, attrib, **extra)

        for m in mechanism:
            mechanism       = Element("mechanism")
            mechanism.text  = m.value
            self.append(mechanism)

    def success(self) -> bytes:
        elem = Element("success", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        return ElementTree.tostring(elem)
    
    def not_authorized(self) -> bytes:
        elem    = Element("failure", attrib = {"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        forbid  = Element("not-authorized")
        elem.append(forbid)
        return ElementTree.tostring(elem)
            