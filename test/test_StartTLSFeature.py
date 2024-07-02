from pyjabber.features.StartTLSFeature import StartTLSFeature
import pytest
from xml.etree import ElementTree as ET
from enum import Enum

class Signal(Enum):
    RESET = 0
    DONE = 1

class FeatureInterface:
    def feed(self, element: ET.Element):
        pass

class TLS(FeatureInterface):
    def __init__(self):
        pass

    def feed(self, element: ET.Element):
        pass


def test_initialization_required():
    starttls_feature = StartTLSFeature()
    assert starttls_feature.tag == "starttls"
    assert starttls_feature.attrib == {"xmlns": "urn:ietf:params:xml:ns:xmpp-tls"}
    assert len(starttls_feature) == 1
    assert starttls_feature[0].tag == "required"

def test_initialization_not_required():
    starttls_feature = StartTLSFeature(required=False)
    assert starttls_feature.tag == "starttls"
    assert starttls_feature.attrib == {"xmlns": "urn:ietf:params:xml:ns:xmpp-tls"}
    assert len(starttls_feature) == 0

def test_proceed_response():
    starttls_feature = StartTLSFeature()
    proceed_response = starttls_feature.proceed_response()
    expected_response = b'<proceed xmlns="urn:ietf:params:xml:ns:xmpp-tls" />'
    assert proceed_response == expected_response

if __name__ == "__main__":
    pytest.main()

