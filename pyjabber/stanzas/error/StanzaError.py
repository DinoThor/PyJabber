from xml.etree import ElementTree as ET

class StanzaError():
    def __init__(self) -> None:
        self.error_root = ET.Element("error")
        self._ns        = "urn:ietf:params:xml:ns:xmpp-stanzas"

    def bad_request(self):
        pass

    def feature_not_implemented(self):
        # child_1 = ET.Element("feature-not-implemented", attrib = { "xmlns" : self._ns })
        # child_2 = ET.Element(
        #     "unsupported", 
        #     attrib = { 
        #         "xmlns": "http://jabber.org/protocol/pubsub#errors",
        #         'feature': ""
        #     })