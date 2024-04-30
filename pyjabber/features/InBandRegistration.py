from enum import Enum
from xml.etree import ElementTree as ET


class InBandRegistration(ET.Element):
    def __init__(
            self, 
            tag         : str = "register", 
            attrib      : dict[str, str] = {
                "xmlns" : "http://jabber.org/features/iq-register"
            },
            **extra : str) -> None:
        
        super().__init__(tag, attrib, **extra)  


def conflict_error(id: str):
    return f"<iq id='{id}' type='error' from='localhost'><error type='cancel'><conflict xmlns='urn:ietf:params:xml:ns:xmpp-stanzas' /><text xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'>The requested username already exists.</text></error></iq>".encode()

def result(id: str):
    return f"<iq type='result' id='{id}' from='localhost'/>".encode()
