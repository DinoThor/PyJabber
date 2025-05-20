import pytest
from unittest.mock import Mock, MagicMock, patch
from xml.etree import ElementTree as ET

from pyjabber.utils import ClarkNotation as CN
from pyjabber.stream.StreamHandler import Signal
from pyjabber.network.XMLParser import XMLParser


@pytest.fixture
def setup():
    with patch('pyjabber.stream.StreamHandler.metadata') as mock_meta:
        transport = Mock()
        starttls = Mock()
        mock_meta.HOST = 'localhost'

        return XMLParser(transport, starttls)

def test_initialization(setup):
    handler = setup

    assert handler._state == XMLParser.StreamState.CONNECTED
    assert handler._transport is not None
    assert handler._stanzaHandler is None
    assert handler._streamHandler is not None
    assert handler._stack == []

def test_transport_property(setup):
    handler = setup

    new_transport = Mock()
    handler.transport = new_transport

    assert handler.transport == new_transport
    assert handler._streamHandler.transport == new_transport


def test_start_element_ns_stream(setup):
    handler = setup

    attrs = {("http://etherx.jabber.org/streams", "version"): "1.0"}
    handler.startElementNS(("http://etherx.jabber.org/streams", "stream"), "stream", attrs)

    assert handler._transport.write.call_count == 2
    assert len(handler._stack) == 1
    assert handler._stack[0].tag == CN.clarkFromTuple(("http://etherx.jabber.org/streams", "stream"))


def test_start_element_ns_normal_element(setup):
    handler = setup

    attrs = {("namespace", "attr"): "value"}
    handler._stack.append(ET.Element("dummy"))

    handler.startElementNS(("namespace", "element"), "element", attrs)
    assert len(handler._stack) == 2
    assert handler._stack[-1].tag == CN.clarkFromTuple(("namespace", "element"))
    assert handler._stack[-1].attrib == {CN.clarkFromTuple(("namespace", "attr")): "value"}


def test_start_element_ns_invalid(setup):
    handler = setup

    with pytest.raises(Exception):
        handler.startElementNS(("invalid", "element"), "element", {})


def test_end_element_ns_stream(setup):
    handler = setup
    handler._stack.append(ET.Element("{http://etherx.jabber.org/streams}stream"))

    handler.endElementNS(("http://etherx.jabber.org/streams", "stream"), "stream")

    handler._transport.write.assert_called_once_with(b'</stream:stream>')
    assert len(handler._stack) == 0


def test_end_element_ns_normal_element(setup):
    handler = setup

    parent = ET.Element(CN.clarkFromTuple(("namespace", "parent")))
    child = ET.Element(CN.clarkFromTuple(("namespace", "child")))

    handler._stack.append(parent)
    handler._stack.append(child)

    handler.endElementNS(("namespace", "child"), "child")

    assert len(handler._stack) == 1
    assert len(handler._stack[0]) == 1
    assert handler._stack[0][0].tag == CN.clarkFromTuple(("namespace", "child"))

def test_end_element_ns_invalid_stack(setup):
    handler = setup

    with pytest.raises(Exception):
        handler.endElementNS(("namespace", "element"), "element")


def test_end_element_ns_mismatched_tag(setup):
    handler = setup
    handler._stack.append(ET.Element("different"))

    with pytest.raises(Exception):
        handler.endElementNS(("namespace", "element"), "element")


@patch('pyjabber.stream.StanzaHandler.StanzaHandler')
@patch('pyjabber.stream.StreamHandler.StreamHandler')
@patch('pyjabber.stream.StanzaHandler.PluginManager')
@patch('pyjabber.stream.StanzaHandler.Presence')
def test_end_element_ns_stream_handling(mock_plugin_manager, mock_presence, mock_handle_open_stream, mock_stream_handler, setup):
    handler = setup
    handler._stack.append(ET.Element("{http://etherx.jabber.org/streams}stream"))

    mock_plugin_manager.return_value = MagicMock()
    mock_presence.return_value = MagicMock()

    elem = ET.Element(CN.clarkFromTuple(("namespace", "dummy")))
    handler._stack.append(elem)

    mock_handle_open_stream.return_value = Signal.DONE
    mock_stream_handler.handle_open_stream.return_value = Signal.DONE
    handler._streamHandler = mock_stream_handler

    with patch('pyjabber.network.XMLParser.StanzaHandler') as mock_stanza_handler:
        handler.endElementNS(("namespace", "dummy"), "dummy")

    assert handler._state == XMLParser.StreamState.READY


def test_characters(setup):
    handler = setup
    parent = ET.Element("parent")
    child = ET.SubElement(parent, "child")
    handler._stack.append(parent)

    # Verificación cuando el elemento tiene hijos
    handler.characters("content")
    assert child.tail == "content"

    # Verificación cuando el elemento no tiene hijos
    handler._stack[-1] = ET.Element("parent_no_children")
    handler.characters("more content")
    assert handler._stack[-1].text == "more content"
    handler.characters(" additional content")
    assert handler._stack[-1].text == "more content additional content"

if __name__ == "__main__":
    pytest.main()
