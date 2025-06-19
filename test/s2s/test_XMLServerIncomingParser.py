import pytest
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
from pyjabber.stream.server.incoming.StanzaServerIncomingHandler import StanzaServerIncomingHandler
from pyjabber.stream.server.incoming.StreamServerIncomingHandler import StreamServerIncomingHandler
from pyjabber.utils import ClarkNotation as CN
from pyjabber.network.server.XMLServerIncomingParser import XMLServerIncomingParser, StreamState, Signal

@pytest.fixture
def setup_parser():
    host = 'host'
    buffer = MagicMock()
    starttls = MagicMock()
    connection_manager = MagicMock()
    queue_message = MagicMock()
    parser = XMLServerIncomingParser(host, buffer, starttls, connection_manager, queue_message)
    return parser, buffer, connection_manager

def test_initialization(setup_parser):
    parser, buffer, connection_manager = setup_parser
    assert isinstance(parser._streamHandler, StreamServerIncomingHandler)

@patch.object(StreamServerIncomingHandler, 'handle_open_stream', MagicMock())
def test_start_element_ns_stream_start(setup_parser):
    parser, buffer, connection_manager = setup_parser
    name = ("http://etherx.jabber.org/streams", "stream")
    attrs = {("http://www.w3.org/XML/1998/namespace", "lang"): "en"}

    parser.startElementNS(name, None, attrs)

    buffer.write.assert_called()
    parser._streamHandler.handle_open_stream.assert_called()

def test_start_element_ns_nested_element(setup_parser):
    parser, buffer, connection_manager = setup_parser
    name = ("namespace", "element")
    attrs = {("namespace", "attr"): "value"}

    parser._stack.append(Element('dummy'))

    parser.startElementNS(name, None, attrs)
    assert len(parser._stack) == 2
    assert parser._stack[-1].tag == CN.clarkFromTuple(name)

def test_start_element_ns_exception(setup_parser):
    parser, buffer, connection_manager = setup_parser
    name = ("wrong_namespace", "element")

    with pytest.raises(Exception):
        parser.startElementNS(name, None, {})

def test_end_element_ns_stream_end(setup_parser):
    parser, buffer, connection_manager = setup_parser
    name = "</stream:stream>"

    parser.endElementNS(name, None)
    buffer.write.assert_called_with(b'</stream>')
    assert not parser._stack

def test_end_element_ns_no_stack_exception(setup_parser):
    parser, buffer, connection_manager = setup_parser
    name = ("namespace", "element")

    with pytest.raises(Exception):
        parser.endElementNS(name, None)

def test_end_element_ns_invalid_stanza_exception(setup_parser):
    parser, buffer, connection_manager = setup_parser
    parser._stack.append(Element('wrong_tag'))
    name = ("namespace", "element")

    with pytest.raises(Exception):
        parser.endElementNS(name, None)

def test_end_element_ns_append_to_stack(setup_parser):
    parser, buffer, connection_manager = setup_parser
    parent = Element('parent')
    child = Element(CN.clarkFromTuple(("namespace", "element")))

    parser._stack.append(parent)
    parser._stack.append(child)
    parser.endElementNS(("namespace", "element"), None)
    assert len(parent) == 1
    assert parent[0] == child


@patch('pyjabber.stream.server.incoming.StanzaServerIncomingHandler.Presence', MagicMock())
@patch.object(StreamServerIncomingHandler, 'handle_open_stream', return_value=Signal.DONE)
def test_end_element_ns_handle_open_stream(mock_handle_open_stream, setup_parser):
    parser, buffer, connection_manager = setup_parser
    parser._stack.append(Element('{http://etherx.jabber.org/streams}stream'))
    parser._state = StreamState.CONNECTED

    elem = Element(CN.clarkFromTuple(("namespace", "element")))
    parser._stack.append(elem)

    parser.endElementNS(("namespace", "element"), None)
    mock_handle_open_stream.assert_called()
    assert parser._state == StreamState.READY
    assert isinstance(parser._stanzaHandler, StanzaServerIncomingHandler)

def test_end_element_ns_signal_reset(setup_parser):
    parser, buffer, connection_manager = setup_parser
    parser._stack.append(Element('{http://etherx.jabber.org/streams}stream'))
    parser._state = StreamState.CONNECTED

    elem = Element(CN.clarkFromTuple(("namespace", "element")))
    parser._stack.append(elem)

    with patch.object(parser._streamHandler, 'handle_open_stream', return_value=Signal.RESET):
        parser.endElementNS(("namespace", "element"), None)
        assert not parser._stack

def test_end_element_ns_ready_state_feed(setup_parser):
    parser, buffer, connection_manager = setup_parser
    parser._stack.append(Element('{http://etherx.jabber.org/streams}stream'))
    parser._state = StreamState.READY
    parser._stanzaHandler = MagicMock()

    elem = Element(CN.clarkFromTuple(("namespace", "element")))
    parser._stack.append(elem)

    parser.endElementNS(("namespace", "element"), None)
    parser._stanzaHandler.feed.assert_called_with(elem)
