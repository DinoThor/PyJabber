from xml.etree import ElementTree
from xml.etree.ElementTree import Element

class StartTLSFeature(ElementTree.Element):
    name = "starttls"
    description = "RFC 6120: Stream feature: StartTLS"

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
