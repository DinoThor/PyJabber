import pytest
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
from pyjabber.network.server.XMLServerOutcomingParser import XMLServerOutcomingParser
from pyjabber.stream.StreamHandler import Signal
from pyjabber.stream.server.outgoing.StreamServerOutgoingHandler import StreamServerOutcomingHandler
from pyjabber.utils import ClarkNotation as CN


@pytest.fixture
def setup_parser():
    buffer = MagicMock()
    starttls = MagicMock()
    connection_manager = MagicMock()
    queue_message = MagicMock()
    host = 'example.com'
    public_host = 'public.example.com'
    parser = XMLServerOutcomingParser(buffer, starttls, connection_manager, queue_message, host, public_host)
    return parser, buffer, connection_manager


def test_initialization(setup_parser):
    parser, buffer, connection_manager = setup_parser
    assert parser._host == 'example.com'
    assert parser._public_host == 'public.example.com'
    assert isinstance(parser._streamHandler, StreamServerOutcomingHandler)


@patch('pyjabber.network.server.outgoing.XMLServerOutcomingParser.Stream')
def test_initial_stream(mock_stream, setup_parser):
    parser, buffer, _ = setup_parser
    mock_stream.Stream.return_value.open_tag.return_value = b'<stream>'

    parser.initial_stream()

    mock_stream.Stream.assert_called_with(
        from_='public.example.com',
        to='example.com',
        xmlns=mock_stream.Namespaces.SERVER.value
    )
    buffer.write.assert_called_with(b'<stream>')


def test_start_element_ns(setup_parser):
    parser, _, _ = setup_parser
    name = ("http://etherx.jabber.org/streams", "stream")
    attrs = {("http://www.w3.org/XML/1998/namespace", "lang"): "en"}

    parser.startElementNS(name, None, attrs)

    assert len(parser._stack) == 1
    assert parser._stack[0].tag == '{http://etherx.jabber.org/streams}stream'


def test_start_element_ns_duplicate_stream(setup_parser):
    parser, _, _ = setup_parser
    parser._stack.append(Element('{http://etherx.jabber.org/streams}stream'))
    name = ("http://etherx.jabber.org/streams", "stream")

    with pytest.raises(Exception):
        parser.startElementNS(name, None, {})


def test_end_element_ns_stream_end(setup_parser):
    parser, buffer, _ = setup_parser
    name = "</stream:stream>"

    parser.endElementNS(name, None)

    buffer.write.assert_called_with(b'</stream>')
    assert not parser._stack


def test_end_element_ns_invalid_stanza(setup_parser):
    parser, _, _ = setup_parser
    parser._stack.append(Element('wrong_tag'))
    name = ("namespace", "element")

    with pytest.raises(Exception):
        parser.endElementNS(name, None)


@patch('pyjabber.stream.server.outgoing.StreamServerOutcomingHandler.StreamServerOutcomingHandler.handle_open_stream')
def test_end_element_ns_reset_signal(mock_handle_open_stream, setup_parser):
    parser, _, _ = setup_parser
    parser._stack.append(Element('{http://etherx.jabber.org/streams}stream'))
    parser._state = parser.StreamState.CONNECTED
    elem = Element(CN.clarkFromTuple(("namespace", "element")))
    parser._stack.append(elem)

    mock_handle_open_stream.return_value = Signal.RESET

    with patch.object(parser, 'initial_stream') as mock_initial_stream:
        parser.endElementNS(("namespace", "element"), None)
        assert not parser._stack
        mock_initial_stream.assert_called_once()


if __name__ == "__main__":
    pytest.main()
