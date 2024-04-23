from xml.etree import ElementTree as ET

XMLNS = "urn:ietf:params:xml:ns:xmpp-stanzas"

def feature_not_implemented(xmlns, feature):
    return f"<error type='cancel'><feature-not-implemented xmlns='{XMLNS}'/><unsupported xmlns='{xmlns}#errors'feature='{feature}'/></error>".encode()

def service_unavaliable():
    return f"<error type='cancel'><service-unavailable xmlns='{XMLNS}'/></error>".encode()

def invalid_xml():
    return f"<stream:error><invalid-xmlxmlns='{XMLNS}'/></stream:error></stream:stream>".encode()

def item_not_found():
    return f"<error type='cancel'><item-not-found xmlns='{XMLNS}'/></error>".encode()