import pytest
from unittest.mock import Mock, MagicMock
from xml.etree import ElementTree as ET
import base64

# Ensure this path is correct
from pyjabber.stream.server.incoming.StreamServerIncomingHandler import StreamServerIncomingHandler, Signal, Stage
from pyjabber.features.StartTLSFeature import StartTLSFeature
from pyjabber.features.SASLFeature import SASLFeature, mechanismEnum

@pytest.fixture
def mock_buffer():
    mock = Mock()
    return mock

@pytest.fixture
def mock_connection_manager():
    mock = Mock()
    return mock

@pytest.fixture
def stream_handler(mock_buffer, mock_connection_manager):
    return StreamServerIncomingHandler('mock_host', mock_buffer, 'mock_starttls', mock_connection_manager)

def test_initialization(stream_handler, mock_buffer, mock_connection_manager):
    assert stream_handler._host == 'mock_host'
    assert stream_handler._buffer == mock_buffer
    assert stream_handler._starttls == 'mock_starttls'
    assert stream_handler._connection_manager == mock_connection_manager

def test_handle_open_stream_connected(stream_handler, mock_buffer):
    stream_handler._stage = Stage.CONNECTED
    stream_handler.handle_open_stream()
    mock_buffer.write.assert_called_once()
    assert stream_handler._stage == Stage.OPENED

def test_handle_open_stream_ssl(stream_handler, mock_buffer):
    stream_handler._stage = Stage.SSL
    stream_handler.handle_open_stream()
    mock_buffer.write.assert_called_once()
    assert stream_handler._stage == Stage.SASL

def test_handle_open_stream_auth(stream_handler, mock_buffer):
    stream_handler._stage = Stage.AUTH
    result = stream_handler.handle_open_stream()
    mock_buffer.write.assert_called_once_with(b"<features xmlns='http://etherx.jabber.org/streams'/>")
    assert stream_handler._stage == Stage.READY
    assert result == Signal.DONE

def test_handle_open_stream_exception(stream_handler):
    stream_handler._stage = None
    with pytest.raises(Exception):
        stream_handler.handle_open_stream()

def test_handle_open_stream_starttls(stream_handler, mock_buffer):
    stream_handler._stage = Stage.OPENED
    stream_handler._starttls = Mock()
    starttls_element = ET.Element(StreamServerIncomingHandler.STARTTLS)
    result = stream_handler.handle_open_stream(starttls_element)
    mock_buffer.write.assert_called_once_with(StartTLSFeature().proceed_response())
    stream_handler._starttls.assert_called_once()  # Ensure _starttls was called
    assert stream_handler._stage == Stage.SSL
    assert result == Signal.RESET


def test_handle_open_stream_sasl_auth_with_mechanism(stream_handler, mock_buffer):
    stream_handler._stage = Stage.SASL
    auth_element = ET.Element(StreamServerIncomingHandler.AUTH, attrib={'mechanism': 'EXTERNAL'})
    auth_element.text = base64.b64encode(b'mock_host').decode()
    result = stream_handler.handle_open_stream(auth_element)
    mock_buffer.write.assert_called_once_with(b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
    assert stream_handler._stage == Stage.AUTH
    assert result == Signal.RESET

def test_handle_open_stream_sasl_auth_no_mechanism(stream_handler, mock_buffer):
    stream_handler._stage = Stage.SASL
    auth_element = ET.Element(StreamServerIncomingHandler.AUTH, attrib={'mechanism': 'EXTERNAL'})
    auth_element.text = None  # Explicitly set text to None to trigger the exception
    with pytest.raises(Exception):
        stream_handler.handle_open_stream(auth_element)


def test_handle_open_stream_sasl_auth_invalid_text(stream_handler, mock_buffer):
    stream_handler._stage = Stage.SASL
    auth_element = ET.Element(StreamServerIncomingHandler.AUTH, attrib={'mechanism': 'EXTERNAL'})
    auth_element.text = 'invalid'
    with pytest.raises(Exception):
        stream_handler.handle_open_stream(auth_element)
