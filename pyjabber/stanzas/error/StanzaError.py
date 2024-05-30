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
    """
    <stream:error>
        <invalid-xml
            xmlns='urn:ietf:params:xml:ns:xmpp-streams'/>
    </stream:error>
    </stream:stream>    
    """
    return f"<stream:error><invalid-xml xmlns='{XMLNS}'/></stream:error></stream:stream>".encode()

def item_not_found() -> bytes:
    """
    <error type='cancel'>
        <item-not-found xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
    </error>
    """
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
    """
    <failure xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>
        <not-authorized/>
    </failure>
    """
    return "<failure xmlns='urn:ietf:params:xml:ns:xmpp-sasl'><not-authorized/></failure>".encode()

def service_unavaliable():
    """
    <error type='cancel'>
        <service-unavailable
            xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
    </error>
    """
    return "<error type='cancel'><service-unavailable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>".encode()

