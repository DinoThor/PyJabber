import pytest
import xml.etree.ElementTree as ET

from pyjabber.stanzas.Presence import Presence


def test_presence_initialization():
    tag = "presence"
    attrib = {"type": "available"}
    extra = {"from": "user@example.com"}

    presence = Presence(tag=tag, attrib=attrib, **extra)

    assert presence.tag == tag
    assert presence.attrib["type"] == "available"
    assert presence.attrib["from"] == "user@example.com"

    assert isinstance(presence, ET.Element)

if __name__ == "__main__":
    pytest.main()
