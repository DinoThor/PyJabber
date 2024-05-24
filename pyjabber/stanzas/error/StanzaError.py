from enum import Enum
from xml.etree import ElementTree as ET

"""
<stanza-kind from='intended-recipient' to='sender' type='error'>
    [OPTIONAL to include sender XML here]
    <error [by='error-generator'] type='error-type'>
       <defined-condition xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
        [<text xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'
            xml:lang='langcode'>
        OPTIONAL descriptive text
        </text>]
        [OPTIONAL application-specific condition element]
    </error>
</stanza-kind>
"""

class StanzaError(ET.Element):
    class StanzaKind(Enum):
        MESSAGE = "message"
        PRESENCE= "presence"
        IQ      = "iq"

    def __init__(
            self, 
            type: StanzaKind,
            from_ :str,
            to: str,
            attrib: dict[str, str] = ..., 
            **extra: str) -> None:
        super().__init__(type.value, attrib, **extra)


XMLNS = "urn:ietf:params:xml:ns:xmpp-stanzas"


def bad_request() -> bytes:
     """
    <error type='modify'>
        <bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
    </error>
    """
     return f"<error type='modify'><bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>".encode()

def conflict_error(id: str) -> bytes:
        iq = ET.Element("iq", attrib = {"id": id, "type": "error", "from": "localhost"})
        error = ET.SubElement(iq, "error", attrib = {"type": "cancel"})
        ET.SubElement(error, "conflict", attrib = {"xmlns": "urn:ietf:params:xml:ns:xmpp-stanzas"})
        text = ET.SubElement(error, "text", attrib = {"xmlns": "urn:ietf:params:xml:ns:xmpp-stanzas"})
        text.text = "The requested username already exists"
        return ET.tostring(iq)

def feature_not_implemented(xmlns, feature) -> bytes:
    """
    <error type='cancel'>
        <feature-not-implemented
            xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
        <unsupported
            xmlns='{xmlns}'
            feature='{feature}'/>
    </error>
    """
    return f"<error type='cancel'><feature-not-implemented xmlns='{XMLNS}'/><unsupported xmlns='{xmlns}#errors'feature='{feature}'/></error>".encode()

def invalid_xml() -> bytes:
    return f"<stream:error><invalid-xmlxmlns='{XMLNS}'/></stream:error></stream:stream>".encode()

def item_not_found() -> bytes:
    return f"<error type='cancel'><item-not-found xmlns='{XMLNS}'/></error>".encode()

def not_acceptable(text: str = None) -> bytes:
    """
    <error type='modify'>
        <not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'>
            [OPTIONAL descriptive text]
            <text>
                {ERROR MESSAGE}
            </text>
        </not-acceptable>
    </error>
    """
    if text:
        return f"<error type='modify'><not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'><text>{text}</text></not-acceptable></error>".encode()
    else:
        return f"<error type='modify'><not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>".encode()
         

def not_authorized() -> bytes:
    elem = ET.Element("failure", attrib = {"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
    ET.SubElement(elem, "not-authorized")
    return ET.tostring(elem)

def result(id: str) -> bytes:
    return f"<iq type='result' id='{id}' from='localhost'/>".encode()

def service_unavaliable(type: StanzaError.StanzaKind, from_: str, to: str):
    error = StanzaError(type, from_, to)
    error.append(ET.fromstring(f"<error type='cancel'><service-unavailable xmlns='{XMLNS}'/></error>"))
    return ET.tostring(error)

def success() -> bytes:
        elem = ET.Element("success", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        return ET.tostring(elem)
