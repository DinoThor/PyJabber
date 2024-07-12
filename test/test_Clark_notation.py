import pytest
from pyjabber.utils.ClarkNotation import deglose, clarkFromTuple, isClark
def test_deglose():
    assert deglose("{namespace}tag") == ("namespace", "tag")
    assert deglose("{http://example.com}element") == ("http://example.com", "element")
    assert deglose("{urn:ietf:params:xml:ns:xmpp-stanzas}message") == ("urn:ietf:params:xml:ns:xmpp-stanzas", "message")
    assert deglose("{}empty") == ("", "empty")

def test_clarkFromTuple():
    assert clarkFromTuple(("namespace", "tag")) == "{namespace}tag"
    assert clarkFromTuple(("http://example.com", "element")) == "{http://example.com}element"
    assert clarkFromTuple((None, "tag")) == "tag"

def test_isClark():
    assert isClark("{namespace}tag") is True
    assert isClark("{http://example.com}element") is True
    assert isClark("tag") is False
    assert isClark("{namespace} tag") is False
    assert isClark("{namespace}") is False

if __name__ == "__main__":
    pytest.main()
