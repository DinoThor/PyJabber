import os
import xml.etree.ElementTree as ET
import pytest
from unittest.mock import Mock, MagicMock

from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.server.incoming.StanzaServerIncomingHandler import StanzaServerIncomingHandler
@pytest.fixture
def mock_connection_manager():
    mock = Mock()
    mock.get_server_host.return_value = 'mock_host'
    mock.get_buffer.return_value = [Mock()]
    return mock


@pytest.fixture
def mock_buffer():
    mock = Mock()
    mock.get_extra_info.return_value = ('127.0.0.1', 12345)
    return mock


@pytest.fixture
def stanza_handler(mock_buffer, mock_connection_manager):
    return StanzaServerIncomingHandler(mock_buffer, mock_connection_manager)


def test_initialization(stanza_handler, mock_buffer, mock_connection_manager):
    assert stanza_handler._buffer == mock_buffer
    assert stanza_handler._connection_manager == mock_connection_manager
    assert stanza_handler._peername == ('127.0.0.1', 12345)
    assert stanza_handler._host == 'mock_host'
    assert isinstance(stanza_handler._presenceManager, Presence)


def test_feed_handle_iq(stanza_handler):
    iq_element = ET.Element('{jabber:client}iq')
    stanza_handler.handle_iq = Mock()

    # Redefine the functions dictionary to ensure mock is used
    stanza_handler._functions = {
        "{jabber:client}iq": stanza_handler.handle_iq,
        "{jabber:client}message": stanza_handler.handle_msg,
        "{jabber:client}presence": stanza_handler.handle_pre
    }

    stanza_handler.feed(iq_element)
    stanza_handler.handle_iq.assert_called_once_with(iq_element)


def test_feed_handle_msg(stanza_handler, mock_connection_manager):
    msg_element = ET.Element('{jabber:client}message', attrib={'to': 'user@domain'})

    mock_buffer_1 = MagicMock()
    mock_buffer_2 = MagicMock()

    mock_connection_manager.get_buffer.return_value = [[mock_buffer_1], [mock_buffer_2]]

    stanza_handler._functions = {
        "{jabber:client}iq": stanza_handler.handle_iq,
        "{jabber:client}message": stanza_handler.handle_msg,
        "{jabber:client}presence": stanza_handler.handle_pre
    }

    stanza_handler.feed(msg_element)

    mock_buffer_1.write.assert_called_once_with(ET.tostring(msg_element))
    mock_buffer_2.write.assert_called_once_with(ET.tostring(msg_element))


def test_feed_handle_pre(stanza_handler):
    pre_element = ET.Element('{jabber:client}presence')
    stanza_handler.handle_pre = Mock()

    stanza_handler._functions = {
        "{jabber:client}iq": stanza_handler.handle_iq,
        "{jabber:client}message": stanza_handler.handle_msg,
        "{jabber:client}presence": stanza_handler.handle_pre
    }

    stanza_handler.feed(pre_element)
    stanza_handler.handle_pre.assert_called_once_with(pre_element)


def test_feed_invalid_element(stanza_handler, mock_buffer):
    invalid_element = ET.Element('{jabber:client}invalid')

    stanza_handler._functions = {
        "{jabber:client}iq": stanza_handler.handle_iq,
        "{jabber:client}message": stanza_handler.handle_msg,
        "{jabber:client}presence": stanza_handler.handle_pre
    }

    stanza_handler.feed(invalid_element)
    mock_buffer.write.assert_called_once_with(SE.bad_request())


def test_handle_msg(stanza_handler, mock_connection_manager):
    msg_element = ET.Element('{jabber:client}message', attrib={'to': 'user@domain'})
    mock_receiver_buffer = [Mock()]
    mock_connection_manager.get_buffer.return_value = mock_receiver_buffer

    stanza_handler.handle_msg(msg_element)

    for buffer in mock_receiver_buffer:
        buffer[1].write.assert_called_once_with(ET.tostring(msg_element))


def test_handle_msg(stanza_handler, mock_connection_manager):
    msg_element = ET.Element('{jabber:client}message', attrib={'to': 'user@domain'})

    mock_buffer = MagicMock()

    mock_connection_manager.get_buffer.return_value = [[mock_buffer]]

    stanza_handler.handle_msg(msg_element)

    mock_buffer.write.assert_called_once_with(ET.tostring(msg_element))

def test_handle_iq(stanza_handler):
    iq_element = ET.Element('{jabber:client}iq')
    assert stanza_handler.handle_iq(iq_element) is None



def test_handle_pre(stanza_handler):
    pre_element = ET.Element('{jabber:client}presence')
    assert stanza_handler.handle_pre(pre_element) is None

