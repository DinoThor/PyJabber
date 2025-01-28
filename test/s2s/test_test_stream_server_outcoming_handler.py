import pytest
from unittest.mock import Mock
from xml.etree import ElementTree as ET

# Ensure this path is correct
from pyjabber.stream.server.outcoming.StreamServerOutcomingHandler import StreamServerOutcomingHandler, Signal, Stage

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
    return StreamServerOutcomingHandler('mock_host', mock_buffer, 'mock_starttls', mock_connection_manager)


def test_initialization(stream_handler, mock_buffer, mock_connection_manager):
    assert stream_handler._host == 'mock_host'
    assert stream_handler._buffer == mock_buffer
    assert stream_handler._starttls == 'mock_starttls'
    assert stream_handler._connection_manager == mock_connection_manager


def test_handle_open_stream_ready(stream_handler, mock_buffer, mock_connection_manager):
    stream_handler._stage = Stage.READY
    peer = ('127.0.0.1', 12345)
    mock_buffer.get_extra_info.return_value = peer

    result = stream_handler.handle_open_stream()

    mock_connection_manager.set_server_transport.assert_called_once_with(peer, mock_buffer)
    assert result == Signal.DONE


def test_handle_open_stream_features_starttls(stream_handler, mock_buffer):
    stream_handler._stage = Stage.CONNECTED
    features_element = ET.Element(stream_handler.FEATURES)
    starttls_element = ET.SubElement(features_element, stream_handler.STARTTLS)

    result = stream_handler.handle_open_stream(features_element)

    mock_buffer.write.assert_called_once_with(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
    assert stream_handler._stage == Stage.OPENED
    assert result is None


def test_handle_open_stream_features_mechanisms(stream_handler, mock_buffer):
    mechanisms_element = ET.Element(stream_handler.MECHANISMS)
    mech_element = ET.SubElement(mechanisms_element, 'mechanism')
    mech_element.text = 'EXTERNAL'
    features_element = ET.Element(stream_handler.FEATURES)
    features_element.append(mechanisms_element)

    result = stream_handler.handle_open_stream(features_element)

    mock_buffer.write.assert_called_once_with(
        b"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='EXTERNAL'>=</auth>")
    assert result is None


def test_handle_open_stream_proceed(stream_handler, mock_buffer):
    stream_handler._stage = Stage.OPENED
    stream_handler._starttls = Mock()  # Mock _starttls as a callable
    proceed_element = ET.Element(stream_handler.PROCEED)

    result = stream_handler.handle_open_stream(proceed_element)

    stream_handler._starttls.assert_called_once()
    assert stream_handler._stage == Stage.SSL
    assert result == Signal.RESET


def test_handle_open_stream_success(stream_handler):
    success_element = ET.Element(stream_handler.SUCCESS)

    result = stream_handler.handle_open_stream(success_element)

    assert stream_handler._stage == Stage.READY
    assert result == Signal.RESET
