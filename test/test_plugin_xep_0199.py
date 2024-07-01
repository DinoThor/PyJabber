from xml.etree import ElementTree as ET
from pyjabber.plugins.xep_0199.xep_0199 import Ping

def test_ping_feed_happy_path():
    ping = Ping(jid="user@domain.com")
    element = ET.Element("iq", attrib={"to": "localhost", "id": "1234"})

    result = ping.feed(element)

    expected_result = ET.tostring(
        ET.Element(
            "iq",
            attrib={
                "from": "localhost",
                "id": "1234",
                "to": "localhost",
                "type": "result",
            },
        )
    )

    assert result == [expected_result]

def test_ping_feed_wrong_to_value():
    ping = Ping(jid="user@domain.com")
    element = ET.Element("iq", attrib={"to": "remotehost", "id": "1234"})

    result = ping.feed(element)

    assert result is None

def test_ping_feed_empty_element():
    ping = Ping(jid="user@domain.com")
    element = ET.Element("iq")

    result = ping.feed(element)

    assert result is None

def test_ping_feed_with_invalid_xml():
    ping = Ping(jid="user@domain.com")

    # Simulando una cadena XML inválida
    invalid_xml_string = "<iq to='localhost' id='1234'><invalid<xml></iq>"

    try:
        element = ET.fromstring(invalid_xml_string)
        result = ping.feed(element)
        assert result is None
    except ET.ParseError:
        pass

def test_ping_feed_with_additional_attributes():
    ping = Ping(jid="user@domain.com")
    element = ET.Element("iq", attrib={"to": "localhost", "id": "1234", "extra": "value"})

    result = ping.feed(element)

    expected_result = ET.tostring(
        ET.Element(
            "iq",
            attrib={
                "from": "localhost",
                "id": "1234",
                "to": "localhost",
                "type": "result",
            },
        )
    )

    assert result == [expected_result]
