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
    connections_manager[0]._peerList.clear()

@pytest.fixture(autouse=True)
def setup_logging(caplog):
    # Remover todos los handlers para evitar duplicados
    logger.remove()
    # Configurar loguru para trabajar con caplog
    logger.add(caplog.handler, level="ERROR")


def test_connection(connections_manager):
    connections_manager, _ = connections_manager
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    assert peer in connections_manager._peerList
    assert connections_manager._peerList[peer] == (None, None, [False])


def test_disconnection(connections_manager):
    connections_manager, _ = connections_manager
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    connections_manager.disconnection(peer)
    assert peer not in connections_manager._peerList


def test_get_users_connected(connections_manager):
    connections_manager, _ = connections_manager
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    users_connected = connections_manager.get_users_connected()
    assert users_connected == {peer: (None, None, [False])}


def test_get_buffer(connections_manager):
    connections_manager, _ = connections_manager
    peer = ("127.0.0.1", 12345)
    jid = JID("user@localhost")
    transport = MagicMock(spec=Transport)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, jid, transport)
    buffer = connections_manager.get_buffer(jid)
    assert buffer[0][1] == transport
    assert buffer[0][0] == jid


def test_get_buffer_online(connections_manager):
    connections_manager, _ = connections_manager
    peer = ("127.0.0.1", 12345)
    jid = JID("user@localhost")
    transport = MagicMock(spec=Transport)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, jid, transport)
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
    peer = ("127.0.0.1", 12345)
    jid = JID("user@localhost/res1")
    transport = MagicMock(spec=Transport)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, jid, transport)
    connections_manager.online(jid)
    buffer = connections_manager.get_buffer_online(jid)

    assert buffer[0][0] == jid
    assert buffer[0][1] == transport
    assert buffer[0][2] is True

    connections_manager.online(jid, False)

    buffer = connections_manager.get_buffer_online(jid)

    assert len(buffer) == 0


def test_get_jid(connections_manager):
    connections_manager, _ = connections_manager
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, JID("user@localhost"))
    jid = connections_manager.get_jid(peer)
    assert str(jid) == "user@localhost"


def test_set_jid(connections_manager):
    connections_manager, _ = connections_manager
    peer = ("127.0.0.1", 12345)
    transport = MagicMock(spec=Transport)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, JID("user@localhost"), transport)
    jid, buffer, online = connections_manager._peerList[peer]
    assert str(jid) == "user@localhost"
    assert buffer == transport
    assert online == [False]


def test_set_jid_without_transport(connections_manager):
    connections_manager, _ = connections_manager
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, JID("user@localhost"))
    assert str(connections_manager._peerList[peer][0]) == "user@localhost"


def test_set_jid_key_error(connections_manager):
    connections_manager, log = connections_manager
    peer = ("127.0.0.1", 12345)
    connections_manager.set_jid(peer, JID("user@localhost"))
    log.error.assert_called()


def test_disconnection_key_error(connections_manager, caplog):
    peer = ("127.0.0.1", 12345)
    connections_manager, log = connections_manager
    connections_manager.disconnection(peer)
    assert peer not in connections_manager._peerList
    log.warning.assert_called_with(f"{peer} not present in the online list")
    # assert any("not present in the online list" in record.message for record in caplog.records)


def test_online(connections_manager):
    jid_1 = JID("demo@host/res1")
    jid_2 = JID("demo@host/res2")
    jid_3 = JID("demo@host/res3")
    connections_manager, _ = connections_manager
    connections_manager._peerList = {
        ("127.0.0.1", 12345): (jid_1, MagicMock(), [True]),
        ("127.0.0.1", 12346): (jid_2, MagicMock(), [True]),
        ("127.0.0.1", 12347): (jid_3, MagicMock(), [False])
    }
    connections_manager.online(jid_1)
    connections_manager.online(jid_2, False)
    connections_manager.online(jid_3)

    assert connections_manager._peerList[("127.0.0.1", 12345)][2][0] is True
    assert connections_manager._peerList[("127.0.0.1", 12346)][2][0] is False
    assert connections_manager._peerList[("127.0.0.1", 12347)][2][0] is True


@pytest.mark.skip(reason="no way of currently testing this")
def test_check_server_present_in_list_false(connections_manager):
    host = "server.localhost"
    assert not connections_manager.check_server_present_in_list(host)


@pytest.mark.skip(reason="no way of currently testing this")
def test_get_server_buffer_task_s2s(connections_manager):
    host = "server.localhost"
    connections_manager.get_server_buffer(host)
    connections_manager._task_s2s.assert_called_with(host)

@pytest.mark.skip(reason="no way of currently testing this")
def test_connection_server(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    assert peer in connections_manager._remoteList
    assert connections_manager._remoteList[peer] == {"jid": host, "transport": None}

@pytest.mark.skip(reason="no way of currently testing this")
def test_disconnection_server(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    connections_manager.disconnection_server(peer)
    assert peer not in connections_manager._remoteList

@pytest.mark.skip(reason="no way of currently testing this")
def test_get_server_buffer(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    connections_manager.set_server_transport(peer, transport)
    buffer = connections_manager.get_server_buffer(host)
    assert buffer == (host, transport)

@pytest.mark.skip(reason="no way of currently testing this")
def test_set_server_transport(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, None)
    connections_manager.set_server_transport(peer, transport)
    assert connections_manager._remoteList[peer]["transport"] == transport

@pytest.mark.skip(reason="no way of currently testing this")
def test_check_server_stream_available(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    connections_manager.set_server_transport(peer, transport)
    available = connections_manager.check_server_stream_available(host)
    assert available is True

@pytest.mark.skip(reason="no way of currently testing this")
def test_check_server_present_in_list(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    present = connections_manager.check_server_present_in_list(host)
    assert present is True

@pytest.mark.skip(reason="no way of currently testing this")
def test_get_server_buffer_no_transport(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    connections_manager.connection_server(peer, host, None)
    connections_manager.set_server_transport(peer, None)
    buffer = connections_manager.get_server_buffer(host)
    assert buffer is None

@pytest.mark.skip(reason="no way of currently testing this")
def test_check_server_stream_available_false(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    connections_manager.connection_server(peer, host, None)
    available = connections_manager.check_server_stream_available(host)
    assert available is False
