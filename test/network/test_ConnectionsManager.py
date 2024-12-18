import pytest
from unittest.mock import MagicMock
from pyjabber.network.ConnectionManager import ConnectionManager
from asyncio import Transport

from loguru import logger
import logging


@pytest.fixture
def connections_manager():
    task_s2s_mock = MagicMock()  # Creamos un mock para el argumento requerido
    return ConnectionManager(task_s2s=task_s2s_mock)


def test_connection(connections_manager):
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    assert peer in connections_manager._peerList
    assert connections_manager._peerList[peer] == {"jid": None, "transport": None}


def test_disconnection(connections_manager):
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    connections_manager.disconnection(peer)
    assert peer not in connections_manager._peerList


def test_get_users_connected(connections_manager):
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    users_connected = connections_manager.get_users_connected()
    assert users_connected == {peer: {"jid": None, "transport": None}}


def test_get_buffer(connections_manager):
    peer = ("127.0.0.1", 12345)
    transport = MagicMock(spec=Transport)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, "user@localhost", transport)
    buffer = connections_manager.get_buffer("user@localhost")
    assert buffer == [("user@localhost", transport)]


def test_get_jid(connections_manager):
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, "user@localhost")
    jid = connections_manager.get_jid(peer)
    assert jid == "user@localhost"


def test_set_jid(connections_manager):
    peer = ("127.0.0.1", 12345)
    transport = MagicMock(spec=Transport)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, "user@localhost", transport)
    assert connections_manager._peerList[peer] == {"jid": "user@localhost", "transport": transport}


def test_set_jid_without_transport(connections_manager):
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, "user@localhost")
    assert connections_manager._peerList[peer] == {"jid": "user@localhost", "transport": None}


def test_set_jid_key_error(connections_manager):
    peer = ("127.0.0.1", 12345)
    result = connections_manager.set_jid(peer, "user@localhost")
    assert result is False


@pytest.fixture(autouse=True)
def setup_logging(caplog):
    # Remover todos los handlers para evitar duplicados
    logger.remove()
    # Configurar loguru para trabajar con caplog
    logger.add(caplog.handler, level="ERROR")


def test_disconnection_key_error(connections_manager, caplog):
    peer = ("127.0.0.1", 12345)
    with caplog.at_level(logging.ERROR):
        connections_manager.disconnection(peer)
    assert peer not in connections_manager._peerList
    assert any("not present in the online list" in record.message for record in caplog.records)


def test_check_server_present_in_list_false(connections_manager):
    host = "server.localhost"
    assert not connections_manager.check_server_present_in_list(host)


@pytest.mark.skip(reason="no way of currently testing this")

def test_get_server_buffer_task_s2s(connections_manager):
    host = "server.localhost"
    connections_manager.get_server_buffer(host)
    connections_manager._task_s2s.assert_called_with(host)


@pytest.fixture(autouse=True)
def cleanup(connections_manager):
    yield
    connections_manager._peerList.clear()


def test_connection_server(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    assert peer in connections_manager._remoteList
    assert connections_manager._remoteList[peer] == {"jid": host, "transport": None}


def test_disconnection_server(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    connections_manager.disconnection_server(peer)
    assert peer not in connections_manager._remoteList


def test_get_server_buffer(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    connections_manager.set_server_transport(peer, transport)
    buffer = connections_manager.get_server_buffer(host)
    assert buffer == (host, transport)


def test_set_server_transport(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, None)
    connections_manager.set_server_transport(peer, transport)
    assert connections_manager._remoteList[peer]["transport"] == transport


def test_check_server_stream_available(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    connections_manager.set_server_transport(peer, transport)
    available = connections_manager.check_server_stream_available(host)
    assert available is True


def test_check_server_present_in_list(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    transport = MagicMock(spec=Transport)
    connections_manager.connection_server(peer, host, transport)
    present = connections_manager.check_server_present_in_list(host)
    assert present is True


def test_get_server_buffer_no_transport(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    connections_manager.connection_server(peer, host, None)
    connections_manager.set_server_transport(peer, None)
    buffer = connections_manager.get_server_buffer(host)
    assert buffer is None


def test_check_server_stream_available_false(connections_manager):
    peer = ("127.0.0.1", 12345)
    host = "server.localhost"
    connections_manager.connection_server(peer, host, None)
    available = connections_manager.check_server_stream_available(host)
    assert available is False
