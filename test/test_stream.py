import pytest
from xml.etree.ElementTree import Element
from pyjabber.stream.Stream import Namespaces, Stream, responseStream


def test_namespaces_enum():
    assert Namespaces.XMLSTREAM.value == "http://etherx.jabber.org/streams"
    assert Namespaces.CLIENT.value == "jabber:client"
    assert Namespaces.SERVER.value == "jabber:server"


def test_stream_initialization():
    stream = Stream(
        id_='12345',
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
    assert stream.attrib['xmlns'] == Namespaces.CLIENT.value
    assert stream.attrib['xmlns:stream'] == Namespaces.XMLSTREAM.value


def test_stream_open_tag():
    stream = Stream(
        id_='12345',
        from_='user@example.com',
        to='server@example.com',
        version='1.0',
        xml_lang='en'
    )
    open_tag = stream.open_tag()
    assert open_tag == b"<stream:stream id='12345' from='user@example.com' to='server@example.com' version='1.0' xml:lang='en' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams'>"


def test_response_stream():
    attrs = {
        (None, "from"): "user@example.com",
        (None, "to"): "server@example.com",
        (None, "version"): "1.0",
        ("http://www.w3.org/XML/1998/namespace", "lang"): "en"
    }
    open_tag = responseStream(attrs)
    tag = open_tag.decode()

    assert tag.startswith("<stream:stream id='")
    assert "from='server@example.com'" in tag
    assert "to='user@example.com'" in tag
    assert "version='1.0'" in tag
    assert "xml:lang='en'" in tag
    assert "xmlns='jabber:client'" in tag
    assert "xmlns:stream='http://etherx.jabber.org/streams'" in tag
