from unittest.mock import patch
from xml.etree import ElementTree as ET
from pyjabber.plugins.xep_0199.xep_0199 import Ping
from pyjabber.stream.JID import JID


def test_ping_feed_happy_path():
    with patch('pyjabber.plugins.xep_0199.xep_0199.host') as mock_host:
        mock_host.get.return_value = 'localhost'
        ping = Ping()
        element = ET.Element("iq", attrib={"to": "localhost", "id": "1234"})

        result = ping.feed(JID("demo@localhost/123"), element)

    result = ET.fromstring(result)
    assert result.tag == 'iq'
    assert result.attrib.get('from') == 'localhost'
    assert result.attrib.get('type') == 'result'
    assert result.attrib.get('id') == '1234'
    assert result.attrib.get('to') == 'demo@localhost/123'

def test_ping_feed_wrong_to_value():
    with patch('pyjabber.plugins.xep_0199.xep_0199.host') as mock_host:
        mock_host.get.return_value = 'localhost'
        ping = Ping()
        element = ET.Element("iq", attrib={"to": "remotehost", "id": "1234"})

        result = ping.feed(JID("demo@localhost/123"), element)

        assert result is None

def test_ping_feed_empty_element():
    with patch('pyjabber.plugins.xep_0199.xep_0199.host') as mock_host:
        ping = Ping()
        element = ET.Element("iq")

        result = ping.feed(JID("demo@localhost/123"), element)

        assert result is None

def test_ping_feed_with_invalid_xml():
    with patch('pyjabber.plugins.xep_0199.xep_0199.host') as mock_host:
        mock_host.get.return_value = 'localhost'
        ping = Ping()

    # Simulando una cadena XML inválida
    invalid_xml_string = "<iq to='localhost' id='1234'><invalid<xml></iq>"

    try:
        element = ET.fromstring(invalid_xml_string)
        result = ping.feed(JID("demo@localhost/123"), element)
        assert result is None
    except ET.ParseError:
        pass

def test_ping_feed_with_additional_attributes():
    with patch('pyjabber.plugins.xep_0199.xep_0199.host') as mock_host:
        mock_host.get.return_value = 'localhost'
        ping = Ping()

        element = ET.Element("iq", attrib={"to": "localhost", "id": "1234", "extra": "value"})

        result = ping.feed(JID("demo@localhost/123"), element)
        result = ET.fromstring(result)

        assert result.tag == 'iq'
        assert result.attrib.get('from') == 'localhost'
        assert result.attrib.get('type') == 'result'
        assert result.attrib.get('id') == '1234'
        assert result.attrib.get('to') == 'demo@localhost/123'

