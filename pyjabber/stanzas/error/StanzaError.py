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

def feature_not_implemented(xmlns, feature):
    return f"<error type='cancel'><feature-not-implemented xmlns='{XMLNS}'/><unsupported xmlns='{xmlns}#errors'feature='{feature}'/></error>".encode()

def service_unavaliable(type: StanzaError.StanzaKind, from_: str, to: str):
    error = StanzaError(type, from_, to)
    error.append(ET.fromstring(f"<error type='cancel'><service-unavailable xmlns='{XMLNS}'/></error>"))
    return ET.tostring(error)

def invalid_xml():
    return f"<stream:error><invalid-xmlxmlns='{XMLNS}'/></stream:error></stream:stream>".encode()

def item_not_found():
    return f"<error type='cancel'><item-not-found xmlns='{XMLNS}'/></error>".encode()