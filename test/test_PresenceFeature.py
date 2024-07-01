import pytest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.features.feature_utils import RosterUtils as RU

@pytest.fixture
def setup_presence():
    with patch('pyjabber.features.feature_utils.RosterUtils.retrieve_roster') as mock_retrieve_roster:
        with patch('pyjabber.features.feature_utils.RosterUtils.update') as mock_update:
            with patch('pyjabber.network.ConnectionManager.ConnectionManager') as MockConnectionsManager:
                mock_connections = MockConnectionsManager.return_value
                jid = 'user2@localhost'
                presence = Presence(jid, mock_connections)
                yield presence, mock_connections, mock_retrieve_roster, mock_update

def elements_are_equal(e1, e2):
    if e1.tag != e2.tag or e1.attrib != e2.attrib or e1.text != e2.text:
        return False
    return all(elements_are_equal(c1, c2) for c1, c2 in zip(e1, e2))

def test_handle_subscribe(setup_presence):
    presence, mock_connections, mock_retrieve_roster, mock_update = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribe', 'to': 'user@localhost', 'id': '123'})

    # Simular la respuesta de retrieve_roster
    mock_retrieve_roster.side_effect = [
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="none"/>')],  # Simulación inicial
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="ask"/>')]  # Después de update
    ]

    # Simular la respuesta de update
    mock_update.return_value = '<item jid="user@localhost" subscription="ask"/>'

    mock_connections.get_buffer.return_value = [MagicMock()]

    presence._jid = 'user2@localhost'

    result = presence.handle_subscribe(element)

    assert result is None
    mock_retrieve_roster.assert_called_with('user2@localhost')

    # Comparar elementos XML
    expected_item = ET.Element('item', attrib={'jid': 'user@localhost', 'subscription': 'none', 'ask': 'subscribe'})
    actual_call = mock_update.call_args
    assert actual_call is not None
    actual_item = actual_call[1]['item']
    assert elements_are_equal(expected_item, actual_item)
    assert actual_call[1]['id'] == 1
def test_handle_subscribed(setup_presence):
    presence, mock_connections, mock_retrieve_roster, mock_update = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribed', 'to': 'user@localhost', 'id': '123'})

    presence._jid = 'user2@localhost'

    # Simular la respuesta de retrieve_roster
    mock_retrieve_roster.side_effect = [
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="from"/>')],
        [(1, 'user@localhost', '<item jid="user2@localhost" subscription="none"/>')]
    ]

    # Simular las respuestas de get_buffer_by_jid
    mock_connections.get_buffer_by_jid.side_effect = [
        [MagicMock()],
        [MagicMock()]
    ]

    result = presence.handle_subscribed(element)

    assert result is None



def test_handle_unsubscribed(setup_presence):
    presence, mock_connections, mock_retrieve_roster, mock_update = setup_presence
    element = ET.Element('presence', attrib={'type': 'unsubscribed', 'to': 'user@localhost', 'id': '123'})

    presence._jid = 'user2@localhost'

    # Simular la respuesta de retrieve_roster
    mock_retrieve_roster.side_effect = [
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="both"/>')]
    ]

    # Simular la respuesta de get_buffer_by_jid
    mock_connections.get_buffer.return_value = [MagicMock()]

    result = presence.handle_unsubscribed(element)

    assert result is None

def test_handle_unavailable(setup_presence):
    presence, mock_connections, mock_retrieve_roster, mock_update = setup_presence
    element = ET.Element('presence', attrib={'type': 'unavailable', 'from': 'user2@localhost', 'id': '123'})

    presence._jid = 'user2@localhost'  # Inicializar _jid

    mock_retrieve_roster.retriveRoster.return_value = [
        (1, 'user@localhost', '<item jid="user2@localhost" subscription="both"/>')
    ]

    mock_connections.get_buffer_by_jid.return_value = [MagicMock()]

    result = presence.handle_unavailable(element)

    assert result is None

def test_feed_handle_initial_presence(setup_presence):
    presence, mock_connections, mock_retrieve_roster, mock_update = setup_presence
    element = ET.Element('presence', attrib={'id': '123'})
    jid = 'user@localhost'

    mock_retrieve_roster.return_value = [
        (1, 'user2@localhost', '<item jid="user2@localhost" subscription="both"/>')
    ]

    buffer_mock = MagicMock()
    mock_connections.get_buffer.return_value = [buffer_mock]

    result = presence.feed(element)

    assert result is None
    mock_retrieve_roster.assert_called_once_with('user2@localhost')
    mock_connections.get_buffer.assert_called_once_with('user2@localhost')
    buffer_mock[-1].write.assert_called_once()



def test_handle_initial_presence(setup_presence):
    presence, mock_connections, mock_retrieve_roster, mock_update = setup_presence
    element = ET.Element('presence', attrib={'id': '123'})
    presence._jid = 'user@localhost'

    mock_retrieve_roster.return_value = [
        (1, 'user2@localhost', '<item jid="user2@localhost" subscription="both"/>')
    ]

    buffer_mock = MagicMock()
    mock_connections.get_buffer.return_value = [buffer_mock]

    presence.handle_initial_presence(element)

    mock_retrieve_roster.assert_called_once_with('user@localhost')
    mock_connections.get_buffer.assert_called_once_with('user2@localhost')
    buffer_mock[-1].write.assert_called_once()


if __name__ == "__main__":
    pytest.main()
