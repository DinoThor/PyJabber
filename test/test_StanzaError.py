from unittest.mock import patch

import pytest
import xml.etree.ElementTree as ET

from pyjabber.stanzas.error.StanzaError import (
    bad_request,
    conflict_error,
    feature_not_implemented,
    invalid_xml,
    item_not_found,
    not_acceptable,
    not_authorized,
    service_unavaliable,
    XMLNS
)


def test_bad_request():
    expected = b"<error type='modify'><bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
    assert bad_request() == expected

def test_conflict_error():
    id = "123"
    with patch('pyjabber.stanzas.error.StanzaError.metadata') as mock_meta:
        mock_meta.HOST = 'localhost'
        result = conflict_error(id)

    root = ET.fromstring(result)

    assert root.tag == "iq"
    assert root.attrib["id"] == id
    assert root.attrib["type"] == "error"
    assert root.attrib["from"] == "localhost"

    error = root.find("error")
    assert error is not None
    assert error.attrib["type"] == "cancel"

    conflict = error.find(f"{{{XMLNS}}}conflict")
    if conflict is None:
        print(ET.tostring(root, encoding='unicode'))
    assert conflict is not None
    assert conflict.tag == f"{{{XMLNS}}}conflict"

    text = error.find(f"{{{XMLNS}}}text")
    assert text is not None
    assert text.tag == f"{{{XMLNS}}}text"
    assert text.text == "The requested username already exists"
def test_feature_not_implemented():
    ns = "custom:namespace"
    feature = "some_feature"
    expected = f"<error type='cancel'><feature-not-implemented xmlns='{XMLNS}'/><unsupported "f"xmlns='{ns}' feature='{feature}'/></error>".encode()
    assert feature_not_implemented(feature, ns) == expected


def test_invalid_xml():
    expected = f"<stream:error><invalid-xml xmlns='{XMLNS}'/></stream:error></stream:stream>".encode()
    assert invalid_xml() == expected


def test_item_not_found():
    expected = b"<error type='cancel'><item-not-found xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
    assert item_not_found() == expected


def test_not_acceptable_with_text():
    text = "Error message"
    expected = f"<error type='modify'><not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'><text>{text}</text></not-acceptable></error>".encode()
    assert not_acceptable(text) == expected


def test_not_acceptable_without_text():
    expected = b"<error type='modify'><not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
    assert not_acceptable() == expected


def test_not_authorized():
    expected = b"<failure xmlns='urn:ietf:params:xml:ns:xmpp-sasl'><not-authorized/></failure>"
    assert not_authorized() == expected


def test_service_unavaliable():
    expected = b"<error type='cancel'><service-unavailable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
    assert service_unavaliable() == expected


if __name__ == "__main__":
    pytest.main()
