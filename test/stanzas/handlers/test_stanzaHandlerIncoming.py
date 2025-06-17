from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET
import pickle

import pytest

from pyjabber.stream.server.incoming.StanzaServerIncomingHandler import StanzaServerIncomingHandler
from pyjabber.features.presence.PresenceFeature import PresenceType
from pyjabber.stream.JID import JID
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.StanzaHandler import StanzaHandler, InternalServerError


@pytest.fixture(scope='function')
def setup():
    mock_buffer = MagicMock()
    mock_buffer.get_extra_info.return_value = '127.0.0.1'

    with patch('pyjabber.stream.StanzaHandler.ConnectionManager') as MockConnectionsManager, \
         patch('pyjabber.stream.StanzaHandler.PluginManager') as MockPluginManager, \
         patch('pyjabber.stream.StanzaHandler.metadata') as mock_metadata, \
         patch('pyjabber.stream.StanzaHandler.Presence') as MockPresence, \
         patch('pyjabber.stream.StanzaHandler.logger') as mock_logger: \

        MockConnectionsManager.get_jid.return_value = 'user@localhost'
        mock_metadata.HOST = 'localhost'

        handler = StanzaServerIncomingHandler(mock_buffer)
        handler._functions = {
            "{jabber:client}iq": MagicMock(),
            "{jabber:client}message": MagicMock(),
            "{jabber:client}presence": MagicMock()
        }

    yield (handler, mock_buffer, MockConnectionsManager,
           MockPresence, mock_logger, mock_metadata.MESSAGE_QUEUE)


def test_handleMsg_resource(setup):
    handler, mock_buffer, mock_connections, mock_presence, _, mock_queue = setup
    element = Element('message', attrib={"to": "user@localhost/res1"})
    element.tag = "{jabber:server}message"

    mock_server_buffer = MagicMock()
    mock_connections.return_value.get_buffer_online.return_value = [(None, mock_server_buffer, [True])]

    handler.handle_msg(element)

    mock_server_buffer.write.assert_called_once_with(ET.tostring(element))
    mock_queue.put_nowait.assert_not_called()


def test_handleMsg_resource_queue(setup):
    handler, mock_buffer, mock_connections, mock_presence, _, mock_queue = setup
    element = Element('message', attrib={"to": "user@localhost/res1"})
    element.tag = "{jabber:server}message"

    mock_server_buffer = MagicMock()
    mock_connections.return_value.get_buffer_online.return_value = []

    with patch('pyjabber.stream.server.incoming.StanzaServerIncomingHandler.JID') as mock_jid:
        mock_jid.return_value = JID('user@localhost/res1')
        handler.handle_msg(element)

    mock_server_buffer.write.assert_not_called()
    mock_queue.put_nowait.assert_called_with(('MESSAGE', mock_jid.return_value,  ET.tostring(element)))


def test_handleMsg_enqueue_resource(setup):
    handler, mock_buffer, mock_connections, mock_presence, _, mock_queue = setup
    element = Element('message', attrib={"to": "user@localhost/res1"})
    element.tag = "{jabber:client}message"

    mock_connections.return_value.get_buffer_online.return_value = []
    mock_presence.return_value.most_priority.return_value = []

    handler.handle_msg(element)

    args = mock_queue.put_nowait.call_args.args[0]
    assert args[0] == 'MESSAGE'
    assert args[1] == JID('user@localhost/res1')
    assert args[2] == ET.tostring(element)


def test_handleMsg_bare(setup):
    handler, mock_buffer, mock_connections, mock_presence, _, mock_queue = setup
    element = Element('message', attrib={"to": "user@localhost"})
    element.tag = "{jabber:client}message"

    buffer_mock_1 = MagicMock()
    buffer_mock_2 = MagicMock()

    mock_connections.return_value.get_buffer_online.side_effect = [
        [(MagicMock(), buffer_mock_1, [True])], [(MagicMock(), buffer_mock_2, [True])]
    ]
    mock_presence.return_value.most_priority.return_value = [
        ('res1', PresenceType.AVAILABLE, None, None, None),
        ('res2', PresenceType.AVAILABLE, None, None, None)
    ]

    handler.handle_msg(element)

    mock_queue.put_nowait.assert_not_called()
    assert str(mock_presence.return_value.most_priority.call_args[0][0]) == 'user@localhost'
    con_calls = mock_connections.return_value.get_buffer_online.call_args_list
    assert str(con_calls[0][0][0]) == 'user@localhost/res1'
    assert str(con_calls[1][0][0]) == 'user@localhost/res2'
    buffer_mock_1.write.assert_called_with(ET.tostring(element))
    buffer_mock_2.write.assert_called_with(ET.tostring(element))


def test_handleMsg_bare_queue(setup):
    handler, mock_buffer, mock_connections, mock_presence, _, mock_queue = setup
    element = Element('message', attrib={"to": "user@localhost"})
    element.tag = "{jabber:client}message"

    mock_presence.return_value.most_priority.return_value = []
    with patch('pyjabber.stream.server.incoming.StanzaServerIncomingHandler.JID') as mock_jid:
        mock_jid.return_value = JID('user@localhost')
        handler.handle_msg(element)

    mock_queue.put_nowait.assert_called_with(('MESSAGE', mock_jid.return_value, ET.tostring(element)))
    mock_connections.return_value.get_buffer_online.assert_not_called()
