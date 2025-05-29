import pytest
from xml.etree.ElementTree import Element
from pyjabber.stream.Stream import Stream


def test_namespaces_enum():
    assert Stream.Namespaces.XMLSTREAM.value == "http://etherx.jabber.org/streams"
    assert Stream.Namespaces.CLIENT.value == "jabber:client"
    assert Stream.Namespaces.SERVER.value == "jabber:server"


def test_stream_initialization():
    stream = Stream(
        id='12345',
        from_='user@example.com',
        to='server@example.com',
        version='1.0',
        xml_lang='en'
    )
    assert isinstance(stream, Element)
    assert stream.tag == 'stream:stream'
    assert stream.attrib['id'] == '12345'
    assert stream.attrib['from'] == 'user@example.com'
    assert stream.attrib['to'] == 'server@example.com'
    assert stream.attrib['version'] == '1.0'
    assert stream.attrib['xml:lang'] == 'en'
    assert stream.attrib['xmlns'] == Stream.Namespaces.CLIENT.value
    assert stream.attrib['xmlns:stream'] == Stream.Namespaces.XMLSTREAM.value


def test_stream_open_tag():
    stream = Stream(
        id='12345',
        from_='user@example.com',
        to='server@example.com',
        version='1.0',
        xml_lang='en'
    )
    open_tag = stream.open_tag()
    assert open_tag == b"<stream:stream id='12345' from='user@example.com' to='server@example.com' version='1.0' xml:lang='en' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams'>"


def test_response_stream_client():
    attrs = {
        (None, "from"): "user@example.com",
        (None, "to"): "server@example.com",
        (None, "version"): "1.0",
        ("http://www.w3.org/XML/1998/namespace", "lang"): "en"
    }
    open_tag = Stream.responseStream(attrs)
    tag = open_tag.decode()

    assert tag.startswith("<stream:stream id='")
    assert "from='server@example.com'" in tag
    assert "to='user@example.com'" in tag
    assert "version='1.0'" in tag
    assert "xml:lang='en'" in tag
    assert "xmlns='jabber:client'" in tag
    assert "xmlns:stream='http://etherx.jabber.org/streams'" in tag


def test_response_stream_server():
    attrs = {
        (None, "from"): "server.com",
        (None, "to"): "otherser.com",
        (None, "version"): "1.0",
        ("http://www.w3.org/XML/1998/namespace", "lang"): "en"
    }
    open_tag = Stream.responseStream(attrs, True)
    tag = open_tag.decode()

    assert tag.startswith("<stream:stream id='")
    assert "from='otherser.com'" in tag
    assert "to='server.com'" in tag
    assert "version='1.0'" in tag
    assert "xml:lang='en'" in tag
    assert "xmlns='jabber:server'" in tag
    assert "xmlns:stream='http://etherx.jabber.org/streams'" in tag
