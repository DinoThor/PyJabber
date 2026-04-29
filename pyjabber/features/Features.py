from typing import List, Optional
from xml.etree import ElementTree as ET

from pyjabber.features.SASL.Mechanism import MECHANISM


def resource_binding_feature():
    return ET.Element("{urn:ietf:params:xml:ns:xmpp-bind}bind")


def in_band_registration_feature():
    return ET.Element("{http://jabber.org/features/iq-register}register")


def SASL_feature(mechanism_list: Optional[List[MECHANISM]] = None):
    if mechanism_list is None:
        mechanism_list = [MECHANISM.PLAIN]

    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")
    for m in mechanism_list:
        mechanism = ET.SubElement(
            element, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism"
        )
        mechanism.text = m.value

    return element


def start_tls_feature(required: bool = True):
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-tls}starttls")
    if required:
        element.append(ET.Element("required"))

    return element


def start_tls_proceed_response():
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-tls}proceed")
    return ET.tostring(element)
