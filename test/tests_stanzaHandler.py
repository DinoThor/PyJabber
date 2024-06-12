from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET

import pickle
from pyjabber.utils import ClarkNotation as CN
import os

from pyjabber.stream.StanzaHandler import StanzaHandler


def setUp():
    mock_buffer = MagicMock()
    mock_buffer.get_extra_info.return_value = '127.0.0.1'

    with patch('pyjabber.network.ConnectionsManager') as MockConnectionsManager, \
         patch('pyjabber.features.PresenceFeature.Presence') as MockPresence:

        mock_connections = MockConnectionsManager.return_value
        mock_presence = MockPresence.return_value
        mock_connections.get_jid_by_peer.return_value = 'user@domain.com'

        schemas_path = os.path.join(os.path.dirname(__file__), '..', 'pyjabber', 'stream', 'schemas', 'schemas.pkl')
        with open(schemas_path, 'rb') as f:
            schemas = pickle.load(f)

        handler = StanzaHandler(mock_buffer)
        handler._schemas = schemas
        handler._connections = mock_connections
        handler._presenceManager = mock_presence
        handler._functions = {
            "{jabber:client}iq": MagicMock()
        }

    return handler, mock_buffer, mock_connections, mock_presence


def test_feed_valid_element():
    handler, mock_buffer, mock_connections, mock_presence = setUp()

    element = Element('iq', attrib={"to": "localhost", "type": "get"})
    element.tag = "{jabber:client}iq"
    child = Element('query')
    element.append(child)

    handler._functions = {element.tag: MagicMock()}

    handler.feed(element)

    handler._functions[element.tag].assert_called_once_with(element)


@patch('pyjabber.stanzas.error.StanzaError.bad_request')
def test_feed_invalid_element_schema(mock_bad_request):
    handler, mock_buffer, mock_connections, mock_presence = setUp()

    # Creamos un elemento de prueba con la estructura esperada
    element = Element('iq', attrib={"to": "localhost", "type": "get"})
    element.tag = "{jabber:client}iq"
    child = Element('{jabber:client}query')  # Aseguramos que el child tenga el namespace correcto
    element.append(child)

    # Forzamos el esquema para que no sea válido
    schema = handler._schemas[CN.deglose(element.tag)[0]]
    with patch.object(schema, 'is_valid', return_value=False):
        handler.feed(element)

    mock_bad_request.assert_called_once()
    mock_buffer.write.assert_called_once_with(mock_bad_request())


def test_feed_function_key_error():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('unknown', attrib={"to": "localhost"})
    element.tag = "{jabber:client}unknown"
    child = Element('{jabber:client}query')
    element.append(child)

    try:
        handler.feed(element)
    except Exception:
        pass
    else:
        raise AssertionError("Exception not raised")


def test_handleIQ():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('iq', attrib={"to": "localhost"})
    with patch('pyjabber.plugins.PluginManager.PluginManager') as MockPluginManager:
        mock_plugin_manager = MockPluginManager.return_value
        mock_plugin_manager.feed.return_value = 'response'

        handler.handleIQ(element)

        mock_buffer.write.assert_called_once_with('response')


def test_handleMsg():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('message', attrib={"to": "user@domain.com"})
    element.tag = "{jabber:client}message"
    mock_connections.get_buffer_by_jid.return_value = [mock_buffer]

    handler.handleMsg(element)

    mock_buffer.write.assert_called_once_with(ET.tostring(element))


def test_handlePre():
    handler, mock_buffer, mock_connections, mock_presence = setUp()
    element = Element('presence', attrib={"to": "localhost"})
    mock_presence.feed.return_value = 'response'

    handler.handlePre(element)

    mock_buffer.write.assert_called_once_with('response')

