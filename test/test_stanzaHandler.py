from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET
import pickle

import pytest

from pyjabber.utils import ClarkNotation as CN
import os
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.StanzaHandler import StanzaHandler, InternalServerError


@pytest.fixture
def setup():
    mock_buffer = MagicMock()
    mock_buffer.get_extra_info.return_value = '127.0.0.1'
    mock_host = "domain.es"

    with patch('pyjabber.stream.StanzaHandler.ConnectionManager') as MockConnectionsManager, \
         patch('pyjabber.stream.StanzaHandler.PluginManager') as MockPluginManager, \
         patch('pyjabber.stream.StanzaHandler.Presence') as MockPresence, \
         patch('pyjabber.stream.StanzaHandler.logger') as mock_logger:

        MockConnectionsManager.get_jid.return_value = 'user@domain.com'

        handler = StanzaHandler(mock_host, mock_buffer)
        handler._functions = {
            "{jabber:client}iq": MagicMock(),
            "{jabber:client}message": MagicMock(),
            "{jabber:client}presence": MagicMock()
        }

    yield handler, mock_buffer, MockConnectionsManager, MockPresence, mock_logger

def test_feed_valid_element(setup):
    handler, mock_buffer, mock_connections, mock_presence, _ = setup
    element = Element('iq', attrib={"to": "localhost", "type": "get"})
    element.tag = "{jabber:client}iq"
    child = Element('query')
    element.append(child)

    handler.feed(element)

    handler._functions[element.tag].assert_called_once_with(element)


@patch('pyjabber.stanzas.error.StanzaError.feature_not_implemented')
def test_feed_function_key_error(mock_feature_not_implemented, setup):
    handler, mock_buffer, mock_connections, mock_presence, logger = setup
    element = Element('unknown', attrib={"to": "localhost"})
    element.tag = "{jabber:client}unknown"
    child = Element('{jabber:client}query')
    element.append(child)

    try:
        handler.feed(element)
    except (KeyError, InternalServerError):
        pass  # Verify the exception was raised
    else:
        raise AssertionError("Exception not raised")

    # It shouldn't reach this part of the code
    mock_feature_not_implemented.assert_not_called()
    mock_buffer.write.assert_not_called()


def test_handleIQ(setup):
    handler, mock_buffer, mock_connections, mock_presence, _ = setup
    element = Element('iq', attrib={"to": "localhost", "type": "get"})
    child = Element('{jabber:client}query')  # Aseguramos que tenga el namespace adecuado
    element.append(child)

    expected_response = SE.service_unavaliable()

    with patch('pyjabber.stream.StanzaHandler.PluginManager') as MockPluginManager:
        MockPluginManager.feed.return_value = expected_response  # Simulamos la respuesta esperada
        handler._pluginManager = MockPluginManager
        handler.handle_iq(element)
        mock_buffer.write.assert_called_once_with(expected_response)


def test_handleMsg(setup):
    handler, mock_buffer, mock_connections, mock_presence, _ = setup
    element = Element('message', attrib={"to": "user@domain.es"})
    element.tag = "{jabber:client}message"

    mock_server_buffer = MagicMock()
    mock_connections.return_value.get_buffer.return_value=[(None, mock_server_buffer)]

    handler.handle_msg(element)

    mock_server_buffer.write.assert_called_once_with(ET.tostring(element))

@pytest.mark.skip
def test_handleMsg_remote_user(setup):
    handler, mock_buffer, mock_connections, mock_presence, _ = setup
    element = Element('message', attrib={"to": "user@remote.com"})
    element.tag = "{jabber:client}message"
    mock_connections.get_server_buffer.return_value = None
    handler.handle_msg(element)
    mock_queue_message.enqueue.assert_called_once_with('remote.com', ET.tostring(element))

def test_handlePre(setup):
    handler, mock_buffer, mock_connections, mock_presence, _ = setup
    element = Element('presence', attrib={"to": "localhost"})
    mock_presence.return_value.feed.return_value = 'response'
    handler.handle_pre(element)
    mock_buffer.write.assert_called_once_with('response')
