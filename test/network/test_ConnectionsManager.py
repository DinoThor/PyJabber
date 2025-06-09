import pytest
from unittest.mock import MagicMock, patch
from pyjabber.network.ConnectionManager import ConnectionManager
from asyncio import Transport

from loguru import logger

from pyjabber.stream.JID import JID


@pytest.fixture
def connections_manager():
    with patch('pyjabber.network.ConnectionManager.logger') as mock_logger:
        yield ConnectionManager(), mock_logger


@pytest.fixture(autouse=True)
def cleanup(connections_manager):
    connections_manager, _ = connections_manager
    connections_manager.peerList.clear()


@pytest.fixture(autouse=True)
def setup_logging(caplog):
    logger.remove()
    logger.add(caplog.handler, level="ERROR")


def test_connection(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager.connection(peer)
    assert peer in connections_manager._peerList
    assert connections_manager._peerList[peer] == (None, None, [False])


def test_disconnection(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager.connection(peer)
    connections_manager.disconnection(peer)
    assert peer not in connections_manager._peerList


def test_online(connections_manager):
    jid_1 = JID("demo@host/res1")
    jid_2 = JID("demo@host/res2")
    jid_3 = JID("demo@host/res3")
    connections_manager, _ = connections_manager
    connections_manager._peerList = {
        ('127.0.0.1', 12345): (jid_1, MagicMock(), [True]),
        ('127.0.0.1', 12346): (jid_2, MagicMock(), [True]),
        ('127.0.0.1', 12347): (jid_3, MagicMock(), [False])
    }
    connections_manager.online(jid_1)
    connections_manager.online(jid_2, False)
    connections_manager.online(jid_3)

    assert connections_manager._peerList[('127.0.0.1', 12345)][2][0] is True
    assert connections_manager._peerList[('127.0.0.1', 12346)][2][0] is False
    assert connections_manager._peerList[('127.0.0.1', 12347)][2][0] is True


def test_get_users_connected(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager.connection(peer)
    users_connected = connections_manager.peerList
    assert users_connected == {peer: (None, None, [False])}


def test_close(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    mock_transport = MagicMock()
    connections_manager._peerList = {
        ('127.0.0.1', 12345): (JID("demo@localhost"), mock_transport, [True]),
    }
    connections_manager.disconnection = MagicMock()

    connections_manager.close(peer)
    connections_manager.disconnection.assert_called()
    mock_transport.write.assert_called_with('</stream:stream>'.encode())

    connections_manager.close(('127.0.0.1', 54321))
    mock_logger.error.assert_called_with(f"{('127.0.0.1', 54321)} not present in the online list")


def test_get_buffer(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    jid = JID("user@localhost")
    transport = MagicMock(spec=Transport)
    connections_manager._peerList = {
        peer: (jid, transport, [False])
    }
    buffer = connections_manager.get_buffer(jid)
    assert buffer[0][1] == transport
    assert buffer[0][0] == jid


def test_get_buffer_with_resource(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    jid = JID("user@localhost/1234")
    transport = MagicMock(spec=Transport)
    connections_manager._peerList = {
        peer: (jid, transport, [False])
    }
    buffer = connections_manager.get_buffer(jid)
    assert buffer[0][1] == transport
    assert buffer[0][0] == jid


def test_get_buffer_online(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    jid = JID("user@localhost")
    transport = MagicMock(spec=Transport)
    connections_manager._peerList = {
        peer: (jid, transport, [False])
    }

    connections_manager.online(jid)
    buffer = connections_manager.get_buffer_online(jid)

    assert buffer[0][0] == jid
    assert buffer[0][1] == transport
    assert buffer[0][2] is True

    connections_manager.online(jid, False)

    buffer = connections_manager.get_buffer_online(jid)

    assert len(buffer) == 0


def test_get_buffer_online_with_resource(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    jid = JID("user@localhost/res1")
    transport = MagicMock(spec=Transport)
    connections_manager._peerList = {
        peer: (jid, transport, [True])
    }

    buffer = connections_manager.get_buffer_online(jid)

    assert buffer[0][0] == jid
    assert buffer[0][1] == transport
    assert buffer[0][2] is True

    connections_manager.online(jid, False)

    buffer = connections_manager.get_buffer_online(jid)

    assert len(buffer) == 0


def test_update_buffer_peer(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    transport = MagicMock()
    jid = JID("demo@localhost")
    connections_manager._peerList = {
        peer: (jid, transport, [False])
    }
    new_transport = MagicMock
    connections_manager.update_buffer(peer=peer, new_transport=new_transport)
    assert connections_manager._peerList[peer][1] == new_transport
    assert connections_manager._peerList[peer][0] == jid
    assert connections_manager._peerList[peer][2] == [False]


def test_update_buffer_jid(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    transport = MagicMock()
    jid = JID("demo@localhost/123")
    connections_manager._peerList = {
        peer: (jid, transport, [False])
    }
    new_transport = MagicMock
    connections_manager.update_buffer(new_transport=new_transport, jid=jid)
    assert connections_manager._peerList[peer][1] == new_transport
    assert connections_manager._peerList[peer][0] == jid
    assert connections_manager._peerList[peer][2] == [False]


def test_update_buffer_malformed(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    transport = MagicMock()
    jid = JID("demo@localhost/123")
    connections_manager._peerList = {
        peer: (jid, transport, [False])
    }
    new_transport = MagicMock
    connections_manager.update_buffer(new_transport=new_transport)
    mock_logger.warning.assert_called_with(
        "Missing peer OR jid parameter to update transport in client connection. No action will be performed"
    )
    connections_manager.update_buffer(new_transport=new_transport, jid=JID("demo@localhost"))
    mock_logger.warning.assert_called_with(
        "JID must have a resource to update transport"
    )
    connections_manager.update_buffer(new_transport=new_transport, jid=JID("demo2@localhost/123"))
    mock_logger.warning.assert_called_with(
        "Unable to find client with given JID. Check this inconsistency"
    )


def test_get_jid(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, JID("user@localhost"))
    jid = connections_manager.get_jid(peer)
    assert str(jid) == "user@localhost"
    assert connections_manager.get_jid(('127.0.0.1', 54321)) is None


def test_set_jid(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    new_transport = MagicMock(spec=Transport)
    connections_manager._peerList = {
        peer: (None, MagicMock(), [False])
    }
    connections_manager.set_jid(peer, JID("user@localhost"), new_transport)
    jid, buffer, online = connections_manager._peerList[peer]
    assert str(jid) == "user@localhost"
    assert buffer == new_transport
    assert online == [False]


def test_set_jid_without_transport(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, JID("user@localhost"))
    assert str(connections_manager._peerList[peer][0]) == "user@localhost"


def test_set_jid_key_error(connections_manager):
    connections_manager, log = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager.set_jid(peer, JID("user@localhost"))
    log.error.assert_called_with(f"Unable to find {('127.0.0.1', 12345)} during jid/transport update")


def test_update_resource(connections_manager):
    connections_manager, log = connections_manager
    peer = ('127.0.0.1', 12345)
    jid = JID("demo@localhost")
    transport = MagicMock()
    connections_manager._peerList = {
        peer: (jid, transport, [False])
    }
    connections_manager.update_resource(peer, "resource")
    assert connections_manager._peerList[peer][0] == JID("demo@localhost/resource")
    connections_manager.update_resource(('127.0.0.1', 54321), "resource")
    log.error.assert_called_with(f"Unable to find {('127.0.0.1', 54321)} during resource update")


def test_disconnection_key_error(connections_manager, caplog):
    connections_manager, log = connections_manager
    peer = ('127.0.0.1', 5342)
    connections_manager.disconnection(peer)
    assert peer not in connections_manager._peerList
    log.warning.assert_called_with(f"{peer} not present in the online list")
    # assert any("not present in the online list" in record.message for record in caplog.records)


def test_connection_server(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager.connection_server(peer)
    assert peer in connections_manager._remoteList
    assert connections_manager._remoteList[peer] == (None, None)


def test_disconnection_server(connections_manager):
    connections_manager, _ = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager._remoteList = {
        peer: (None, None)
    }
    connections_manager.disconnection_server(peer)
    assert len(connections_manager._remoteList) == 0


def test_disconnection_server_missing_entry(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager._remoteList = {
        peer: (None, None)
    }
    connections_manager.disconnection_server(('127.0.0.1', 54321))
    assert len(connections_manager._remoteList) > 0
    mock_logger.warning.assert_called_with(f"Server {('127.0.0.1', 54321)} not present in the online list")


def test_update_host(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager._remoteList = {
        peer: (None, None)
    }
    connections_manager.update_host(peer, "remote.es")
    assert connections_manager._remoteList[peer][0] == "remote.es"


def test_update_host_no_entry(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    connections_manager._remoteList = {
        peer: (None, None)
    }
    connections_manager.update_host(('127.0.0.1', 54321), "remote.es")
    assert connections_manager._remoteList[peer][0] is None
    mock_logger.warning.assert_called_with("Unable to find server with given peer during host update. Check this inconsistency")


def test_close_server(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    transport = MagicMock()
    connections_manager._remoteList = {
        peer: ("remote.es", transport)
    }
    connections_manager.disconnection_server = MagicMock()
    connections_manager.close_server(peer)
    transport.write.assert_called_with('</stream:stream>'.encode())
    connections_manager.disconnection_server.assert_called()

    connections_manager.close_server(('127.0.0.1', 54321))
    mock_logger.error.assert_called_with(f"{('127.0.0.1', 54321)} not present in the online list")


def test_get_server_buffer_peer(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    transport = MagicMock()
    connections_manager._remoteList = {
        peer: ("remote.es", transport)
    }

    assert connections_manager.get_server_buffer(peer) == transport


def test_get_server_buffer_host(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    transport = MagicMock()
    connections_manager._remoteList = {
        peer: ("remote.es", transport)
    }

    assert connections_manager.get_server_buffer(host="remote.es") == transport


def test_get_server_buffer_no_entry(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    transport = MagicMock()
    connections_manager._remoteList = {
        peer: ("remote.es", transport)
    }

    assert connections_manager.get_server_buffer(('127.0.0.1', 54321)) is None
    mock_logger.error.assert_called_with("Missing peer in the connection list. Check it")


def test_get_server_buffer_malformed(connections_manager):
    connections_manager, mock_logger = connections_manager
    peer = ('127.0.0.1', 12345)
    transport = MagicMock()
    connections_manager._remoteList = {
        peer: ("remote.es", transport)
    }

    assert connections_manager.get_server_buffer() is None
    mock_logger.error.assert_called_with("Missing peer OR host to search for server transport. Returning None")
