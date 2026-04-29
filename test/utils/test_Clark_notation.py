import pytest

from pyjabber.utils.ClarkNotation import break_down, clark_from_tuple, is_clark


def test_deglose():
    assert break_down("{namespace}tag") == ("namespace", "tag")
    assert break_down("{http://example.com}element") == (
        "http://example.com",
        "element",
    )
    assert break_down("{urn:ietf:params:xml:ns:xmpp-stanzas}message") == (
        "urn:ietf:params:xml:ns:xmpp-stanzas",
        "message",
    )
    assert break_down("{}empty") == ("", "empty")


def test_clarkFromTuple():
    assert clark_from_tuple(("namespace", "tag")) == "{namespace}tag"
    assert (
        clark_from_tuple(("http://example.com", "element"))
        == "{http://example.com}element"
    )
    assert clark_from_tuple((None, "tag")) == "tag"


def test_isClark():
    assert is_clark("{namespace}tag") is True
    assert is_clark("{http://example.com}element") is True
    assert is_clark("tag") is False
    assert is_clark("{namespace} tag") is False
    assert is_clark("{namespace}") is False


if __name__ == "__main__":
    pytest.main()
