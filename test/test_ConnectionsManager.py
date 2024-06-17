import pytest
from unittest.mock import MagicMock
from pyjabber.network.ConnectionsManager import ConectionsManager
from asyncio import Transport

@pytest.fixture
def connections_manager():
    return ConectionsManager()

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

def test_get_buffer_by_jid(connections_manager):
    peer = ("127.0.0.1", 12345)
    transport = MagicMock(spec=Transport)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, "user@localhost", transport)
    buffer = connections_manager.get_buffer_by_jid("user@localhost")
    assert buffer == [("user@localhost", transport)]

def test_get_jid_by_peer(connections_manager):
    peer = ("127.0.0.1", 12345)
    connections_manager.connection(peer)
    connections_manager.set_jid(peer, "user@localhost")
    jid = connections_manager.get_jid_by_peer(peer)
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

def test_disconnection_key_error(connections_manager):
    peer = ("127.0.0.1", 12345)
    connections_manager.disconnection(peer)
    # Here, we're just checking that no exception is raised and the logger caught the error.
    assert peer not in connections_manager._peerList

@pytest.fixture(autouse=True)
def cleanup(connections_manager):
    yield
    connections_manager._peerList.clear()

