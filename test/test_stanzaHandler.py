from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET
import pickle
from pyjabber.utils import ClarkNotation as CN
import os
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.StanzaHandler import StanzaHandler

def setUp():
    mock_buffer = MagicMock()
    mock_buffer.get_extra_info.return_value = '127.0.0.1'
    mock_host = "domain.es"

    with patch('pyjabber.network.ConnectionManager.ConnectionManager') as MockConnectionsManager, \
         patch('pyjabber.stream.StanzaHandler.PluginManager') as MockPluginManager, \
         patch('pyjabber.stream.StanzaHandler.Presence') as MockPresence:

        mock_plugin = MagicMock()
        MockPluginManager.return_value = mock_plugin

        mock_presence = MagicMock()
        MockPresence.return_value = mock_presence

        mock_connections = MockConnectionsManager.return_value
        mock_connections.get_jid.return_value = 'user@domain.com'
        MockConnectionsManager.return_value = mock_connections

        handler = StanzaHandler(mock_host, mock_buffer)
        handler._host = mock_host
        handler._functions = {
            "{jabber:client}iq": MagicMock(),
            "{jabber:client}message": MagicMock(),
            "{jabber:client}presence": MagicMock()
        }

    return handler, mock_buffer, mock_connections, mock_presence

def test_feed_valid_element():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('iq', attrib={"to": "localhost", "type": "get"})
    element.tag = "{jabber:client}iq"
    child = Element('query')
    element.append(child)

    handler.feed(element)

    handler._functions[element.tag].assert_called_once_with(element)


@patch('pyjabber.stanzas.error.StanzaError.feature_not_implemented')
def test_feed_function_key_error(mock_feature_not_implemented):
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('unknown', attrib={"to": "localhost"})
    element.tag = "{jabber:client}unknown"
    child = Element('{jabber:client}query')
    element.append(child)

    # Simula que el esquema es válido
    try:
        handler.feed(element)
    except Exception:
        # Verifica que la excepción se lanzó
        pass
    else:
        raise AssertionError("Exception not raised")

    # No debería llegar aquí porque se debe lanzar una excepción
    mock_feature_not_implemented.assert_not_called()
    mock_buffer.write.assert_not_called()

@patch('pyjabber.stanzas.error.StanzaError.feature_not_implemented')
def test_feed_key_error_in_schemas(mock_feature_not_implemented):
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('presence', attrib={"to": "localhost"})
    element.tag = "{jabber:client}unknown"

    with patch.dict(handler._schemas, {}, clear=True):
        handler.feed(element)

    mock_feature_not_implemented.assert_called_once()
    mock_buffer.write.assert_called_once_with(mock_feature_not_implemented())

def test_handleIQ():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('iq', attrib={"to": "localhost", "type": "get"})
    child = Element('{jabber:client}query')  # Aseguramos que tenga el namespace adecuado
    element.append(child)

    expected_response = SE.service_unavaliable()

    with patch('pyjabber.stream.StanzaHandler.PluginManager') as MockPluginManager:
        # mock_plugin_manager = MockPluginManager.return_value
        MockPluginManager.feed.return_value = expected_response # Simulamos la respuesta esperada
        # MockPluginManager.return_value = mock_plugin_manager
        handler.handle_iq(element)
        mock_buffer.write.assert_called_once_with(expected_response)


def test_handleMsg():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('message', attrib={"to": "user@domain.com"})
    element.tag = "{jabber:client}message"

    mock_server_buffer = MagicMock()
    mock_connections.get_server_buffer.return_value = (None, mock_server_buffer)

    handler.handle_msg(element)

    mock_server_buffer.write.assert_called_once_with(ET.tostring(element))


def test_handleMsg_remote_user():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('message', attrib={"to": "user@remote.com"})
    element.tag = "{jabber:client}message"
    mock_connections.get_server_buffer.return_value = None
    handler.handle_msg(element)
    mock_queue_message.enqueue.assert_called_once_with('remote.com', ET.tostring(element))

def test_handlePre():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('presence', attrib={"to": "localhost"})
    mock_presence.feed.return_value = 'response'
    handler.handle_pre(element)
    mock_buffer.write.assert_called_once_with('response')
