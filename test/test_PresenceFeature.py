import pytest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.stanzas.error import StanzaError as SE


@pytest.fixture
def setup_presence():
    with patch('pyjabber.plugins.roster.Roster') as MockRoster:
        with patch('pyjabber.network.ConnectionsManager.ConectionsManager') as MockConnectionsManager:
            mock_roster = MockRoster.return_value
            mock_connections = MockConnectionsManager.return_value
            presence = Presence()
            presence._roster = mock_roster
            presence._connections = mock_connections
            yield presence, mock_roster, mock_connections


def test_feed_subscribe(setup_presence):
    presence, mock_roster, mock_connections = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribe', 'to': 'user@localhost', 'id': '123'})


    mock_roster.retriveRoster.side_effect = [
        [],
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="none"/>')]  # Luego, está en el roster
    ]

    mock_connections.get_buffer_by_jid.return_value = [MagicMock()]

    result = presence.feed(element, 'user2@localhost')

    assert result is None


def test_handle_subscribe(setup_presence):
    presence, mock_roster, mock_connections = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribe', 'to': 'user@localhost', 'id': '123'})

    mock_roster.retriveRoster.side_effect = [
        [],
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="none"/>')]  # Luego, está en el roster
    ]
    mock_connections.get_buffer_by_jid.return_value = [MagicMock()]

    presence._jid = 'user2@localhost'

    result = presence.handleSubscribe(element)

    assert result is None

def test_handle_subscribed(setup_presence):
    presence, mock_roster, mock_connections = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribed', 'to': 'user@localhost', 'id': '123'})

    presence._jid = 'user2@localhost'

    mock_roster.retriveRoster.side_effect = [
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="from"/>')],
        [(1, 'user@localhost', '<item jid="user2@localhost" subscription="none"/>')]
    ]

    mock_connections.get_buffer_by_jid.side_effect = [
        [MagicMock()],
        [MagicMock()]
    ]

    result = presence.handleSubscribed(element)

    assert result is None


def test_handle_unsubscribed(setup_presence):
    presence, mock_roster, mock_connections = setup_presence
    element = ET.Element('presence', attrib={'type': 'unsubscribed', 'to': 'user@localhost', 'id': '123'})

    presence._jid = 'user2@localhost'

    mock_roster.retriveRoster.side_effect = [
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="both"/>')]
    ]

    mock_connections.get_buffer_by_jid.return_value = [MagicMock()]

    result = presence.handleUnsubscribed(element)

    assert result is None


def test_handle_unavailable(setup_presence):
    presence, mock_roster, mock_connections = setup_presence
    element = ET.Element('presence', attrib={'type': 'unavailable', 'from': 'user2@localhost', 'id': '123'})

    presence._jid = 'user2@localhost'  # Inicializar _jid

    mock_roster.retriveRoster.return_value = [
        (1, 'user@localhost', '<item jid="user2@localhost" subscription="both"/>')
    ]

    mock_connections.get_buffer_by_jid.return_value = [MagicMock()]

    result = presence.handleUnavailable(element)

    assert result is None

def test_feed_handle_initial_presence(setup_presence):
    presence, mock_roster, mock_connections = setup_presence
    element = ET.Element('presence', attrib={'id': '123'})
    jid = 'user@localhost'

    mock_roster.retriveRoster.return_value = [
        (1, 'user2@localhost', '<item jid="user2@localhost" subscription="both"/>')
    ]

    buffer_mock = MagicMock()
    mock_connections.get_buffer_by_jid.return_value = [buffer_mock]

    result = presence.feed(element, jid)

    assert result is None
    mock_roster.retriveRoster.assert_called_once_with('user@localhost')
    mock_connections.get_buffer_by_jid.assert_called_once_with('user2@localhost')
    buffer_mock[-1].write.assert_called_once()



def test_handle_initial_presence(setup_presence):
    presence, mock_roster, mock_connections = setup_presence
    element = ET.Element('presence', attrib={'id': '123'})
    presence._jid = 'user@localhost'

    mock_roster.retriveRoster.return_value = [
        (1, 'user2@localhost', '<item jid="user2@localhost" subscription="both"/>')
    ]

    buffer_mock = MagicMock()
    mock_connections.get_buffer_by_jid.return_value = [buffer_mock]

    presence.handleInitialPresence(element)

    mock_roster.retriveRoster.assert_called_once_with('user@localhost')
    mock_connections.get_buffer_by_jid.assert_called_once_with('user2@localhost')
    buffer_mock[-1].write.assert_called_once()



if __name__ == "__main__":
    pytest.main()
