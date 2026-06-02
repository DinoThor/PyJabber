from unittest.mock import MagicMock, Mock, patch
from xml.etree import ElementTree as ET

import pytest

from pyjabber.network.parsers.XMLParser import XMLParser
from pyjabber.stream.negotiators.StreamNegotiator import Signal
from pyjabber.utils import ClarkNotation as CN


@pytest.fixture
def setup():
    with patch("pyjabber.network.parsers.XMLParser.QueueBridge") as mock_queue:
        with patch("pyjabber.network.parsers.XMLParser.asyncio") as mock_asyncio:
            transport = MagicMock()
            starttls = MagicMock()
            # mock_config.host = "localhost"

            return XMLParser(transport, starttls), mock_queue, mock_asyncio


def test_initialization(setup):
    handler, mock_queue, _ = setup

    assert handler._transport is not None
    assert handler._protocol is not None
    assert handler._stream_negotiator is not None
    mock_queue.assert_called_once()
    assert handler._connection_manager is not None
    assert handler._peer is not None
    assert handler._stack == []


def test_start_element_ns_stream(setup):
    handler, _, _ = setup

    attrs = {("http://etherx.jabber.org/streams", "version"): "1.0"}
    handler.startElementNS(
        ("http://etherx.jabber.org/streams", "stream"), "stream", attrs
    )

    assert len(handler._stack) == 1
    assert handler._stack[0].tag == CN.clark_from_tuple(
        ("http://etherx.jabber.org/streams", "stream")
    )
    handler._stream_negotiator.put.assert_called_once()


def test_start_element_ns_normal_element(setup):
    handler, _, _ = setup

    attrs = {("namespace", "attr"): "value"}
    handler._stack.append(ET.Element("dummy"))

    handler.startElementNS(("namespace", "element"), "element", attrs)
    assert len(handler._stack) == 2
    assert handler._stack[-1].tag == CN.clark_from_tuple(("namespace", "element"))
    assert handler._stack[-1].attrib == {
        CN.clark_from_tuple(("namespace", "attr")): "value"
    }


def test_start_element_ns_invalid(setup):
    handler = setup

    with pytest.raises(Exception):
        handler.startElementNS(("invalid", "element"), "element", {})


def test_end_element_ns_stream(setup):
    handler, _, _ = setup
    handler._connection_manager = MagicMock()
    handler._stack.append(ET.Element("{http://etherx.jabber.org/streams}stream"))
    handler._stack.append(ET.Element("{element:ns}element"))

    handler.endElementNS(("element:ns", "element"), "stream")

    assert len(handler._stack) == 0
    handler._stream_negotiator.put.assert_called_once()


def test_end_element_ns_stream_close(setup):
    handler, _, _ = setup
    handler._connection_manager = MagicMock()
    handler._stack.append(ET.Element("{http://etherx.jabber.org/streams}stream"))

    handler.endElementNS(("http://etherx.jabber.org/streams", "stream"), "stream")

    assert len(handler._stack) == 0
    handler._connection_manager.close.assert_called_once()


def test_end_element_ns_normal_element(setup):
    handler, _, _ = setup

    parent = ET.Element(CN.clark_from_tuple(("namespace", "parent")))
    child = ET.Element(CN.clark_from_tuple(("namespace", "child")))

    handler._stack.append(parent)
    handler._stack.append(child)

    handler.endElementNS(("namespace", "child"), "child")

    assert len(handler._stack) == 1
    assert len(handler._stack[0]) == 1
    assert handler._stack[0][0].tag == CN.clark_from_tuple(("namespace", "child"))

def test_end_element_ns_normal_element_to_negotiator(setup):
    handler, _, _ = setup

    opentag = ET.Element(CN.clark_from_tuple(("namespace", "element")))
    endtag = ET.Element(CN.clark_from_tuple(("namespace", "element")))

    handler._stack.append(opentag)
    handler._stack.append(endtag)

    handler.endElementNS(("namespace", "element"), "element")

    assert len(handler._stack) == 1
    assert len(handler._stack[0]) == 1
    assert handler._stack[0][0].tag == CN.clark_from_tuple(("namespace", "child"))


def test_end_element_ns_invalid_stack(setup):
    handler, _, _ = setup

    with pytest.raises(Exception):
        handler.endElementNS(("namespace", "element"), "element")


def test_end_element_ns_mismatched_tag(setup):
    handler = setup
    handler._stack.append(ET.Element("different"))

    with pytest.raises(Exception):
        handler.endElementNS(("namespace", "element"), "element")


@patch("pyjabber.stream.StanzaHandler.StanzaHandler")
@patch("pyjabber.stream.StreamHandler.StreamHandler")
@patch("pyjabber.stream.StanzaHandler.PluginManager")
@patch("pyjabber.stream.StanzaHandler.Presence")
def test_end_element_ns_stream_handling(
    mock_plugin_manager,
    mock_presence,
    mock_handle_open_stream,
    mock_stream_handler,
    setup,
):
    handler = setup
    handler._stack.append(ET.Element("{http://etherx.jabber.org/streams}stream"))

    mock_plugin_manager.return_value = MagicMock()
    mock_presence.return_value = MagicMock()

    elem = ET.Element(CN.clark_from_tuple(("namespace", "dummy")))
    handler._stack.append(elem)

    mock_handle_open_stream.return_value = Signal.DONE
    mock_stream_handler.handle_open_stream.return_value = Signal.DONE
    handler._streamHandler = mock_stream_handler

    with patch(
        "pyjabber.network.parsers.XMLParser.StanzaHandler"
    ) as mock_stanza_handler:
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
