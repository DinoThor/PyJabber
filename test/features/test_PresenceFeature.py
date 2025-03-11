import logging
import os
import sqlite3

import pytest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
from pyjabber.features.presence.PresenceFeature import Presence, PresenceType
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.stream.JID import JID

FILE_PATH = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def setup_database():
    con = sqlite3.connect(':memory:')
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE pendingsub (
            jid VARCHAR(255) NOT NULL,
            item VARCHAR(255) NOT NULL
        )
    ''')
    con.commit()
    yield con
    con.close()


@pytest.fixture
def setup_presence(setup_database):
    with patch('pyjabber.features.presence.PresenceFeature.host') as mock_host, \
         patch('pyjabber.features.presence.PresenceFeature.ConnectionManager') as mock_connections_manager, \
         patch('pyjabber.features.presence.PresenceFeature.connection') as mock_connection, \
         patch('pyjabber.features.presence.PresenceFeature.Roster') as mock_roster:
        con = setup_database
        mock_connection.return_value = con
        mock_host.get.return_value = 'localhost'
        mock_roster.return_value = MagicMock()
        presence = Presence()
        yield presence, mock_connections_manager, mock_roster


def elements_are_equal(e1, e2):
    if e1.tag != e2.tag or e1.attrib != e2.attrib or e1.text != e2.text:
        return False
    return all(elements_are_equal(c1, c2) for c1, c2 in zip(e1, e2))


def test_handle_subscribe(setup_presence):
    presence, mock_connections, mock_roster = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribe', 'to': 'user@localhost', 'id': '123'})
    mock_roster.roster_by_jid.side_effect = [
        [{"id": 1, "item": '<item jid="user@localhost" subscription="none"/>'}],  # Initial simulation
        [{"id": 1, "item": '<item jid="user@localhost" subscription="none" ask="subscribe"/>'}]  # After update
    ]
    mock_connections().get_buffer.return_value = [MagicMock()]
    jid = JID('user2@localhost')
    presence._jid = jid
    presence._roster = mock_roster
    result = presence.handle_subscribe(presence._jid, element)

    assert result is None
    mock_roster.roster_by_jid.assert_called_with(jid)
    expected_item = ET.Element('item', attrib={'jid': 'user@localhost', 'subscription': 'none', 'ask': 'subscribe'})
    args = mock_roster.update_item.call_args.args
    assert args is not None
    actual_item = args[0]
    assert elements_are_equal(expected_item, actual_item)
    assert args[1] == 1

    mock_roster.roster_by_jid.side_effect = None
    mock_connections().get_buffer.return_value = None


def test_handle_subscribe_non_localhost(setup_presence):
    presence, mock_connections, mock_roster = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribe', 'to': 'user@domain.com', 'id': '123'})
    jid = JID('user2@localhost')
    result = presence.handle_subscribe(jid, element)

    assert mock_roster().roster_by_jid.called is False
    assert result is None


def test_handle_subscribe_subscription_both(setup_presence):
    presence, mock_connections, mock_roster = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribe', 'to': 'user@localhost', 'id': '123'})
    mock_roster.roster_by_jid.return_value = [
        {"id": 1, "item": '<item jid="user@localhost" subscription="both"/>'}
    ]
    jid = JID('user2@localhost')
    presence._jid = jid
    presence._roster = mock_roster
    result = presence.handle_subscribe(jid, element)

    expected_response = ET.tostring(ET.Element(
        'presence',
        attrib={
            'from': 'user@localhost',
            'to': 'user2@localhost',
            'id': '123',
            'type': 'subscribed'
        }
    ))

    assert result == expected_response
    mock_roster.roster_by_jid.assert_called()

    mock_roster.roster_by_jid.return_value = None


def test_handle_initial_presence_no_roster_entries(setup_presence):
    presence, mock_connections, mock_roster = setup_presence
    element = ET.Element('presence', attrib={'id': '123'})
    mock_roster.roster_by_jid.return_value = []
    jid = JID('user@localhost/1223')
    presence._jid = jid
    presence._roster = mock_roster
    presence.handle_global_presence(jid, element)

    mock_roster.roster_by_jid.assert_called()
    assert presence._online_status == {
        jid.bare(): [
            (jid.resource, PresenceType.AVAILABLE, None, None, None)
        ]
    }
    mock_connections.get_buffer.assert_not_called()


def test_feed_handle_subscribed(setup_presence):
    presence, mock_connections, mock_roster = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribed', 'to': 'user@localhost', 'id': '123'})
    jid = JID('user2@localhost/1223')
    mock_roster.roster_by_jid.side_effect = [
        [{"id": 1, "item": '<item jid="user2" subscription="none" ask="subscribe"/>'}],  # Initial simulation
        [{"id": 2, "item": '<item jid="user" subscription="none"/>'}]  # After update
    ]
    mock_connections.get_buffer.return_value = []
    presence._jid = jid
    presence._roster = mock_roster
    presence._connections = mock_connections

    expected_fist_update = ET.fromstring('<item jid="user2@localhost" subscription="to"/>')
    expected_second_update = ET.fromstring('<item jid="user@localhost" subscription="from"/>')

    result = presence.feed(jid, element)
    assert result is None
    args_first = mock_roster.update_item.call_args_list[0].args
    assert elements_are_equal(args_first[0], expected_fist_update)
    assert args_first[1] == 1
    args_second = mock_roster.update_item.call_args_list[1].args
    assert elements_are_equal(args_second[0], expected_second_update)
    assert args_second[1] == 2
    assert mock_roster.update_item.call_count == 2


def test_feed_handle_unsubscribed(setup_presence):
    presence, mock_connections, mock_roster = setup_presence
    element = ET.Element('presence', attrib={'type': 'unsubscribed', 'to': 'user@localhost', 'id': '123'})
    jid = JID('user2@localhost/1223')
    mock_roster.roster_by_jid.side_effect = [
        [{"id": 1, "item": '<item jid="user" subscription="to"/>'}]
    ]
    mock_connections.get_buffer.return_value = ([(JID("user@localhost/123"), MagicMock())])
    presence._jid = jid
    presence._roster = mock_roster
    presence._connections = mock_connections
    presence.feed(jid, element)
    mock_roster.roster_by_jid.assert_called_with(jid)
    mock_roster.update_item.assert_called_once()
    mock_connections.get_buffer.assert_called_once()
    assert str(mock_connections.get_buffer.call_args.args[0]) == "user@localhost"

@pytest.mark.skip
def test_feed_handle_unavailable(setup_presence):
    presence, _, _, _, _ = setup_presence
    element = ET.Element('presence', attrib={'type': 'unavailable', 'from': 'user2@localhost', 'id': '123'})
    presence._jid = JID('user2@localhost')
    result = presence.feed(element)
    assert result is None

@pytest.mark.skip
def test_handle_subscribed(setup_presence):
    presence, mock_connections, mock_retrieve_roster, _, _ = setup_presence
    element = ET.Element('presence', attrib={'type': 'subscribed', 'to': 'user@localhost', 'id': '123'})

    presence._jid = JID('user2@localhost')

    mock_retrieve_roster.side_effect = [
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="from"/>')],
        [(1, 'user@localhost', '<item jid="user2@localhost" subscription="none"/>')]
    ]

    mock_connections.get_buffer.side_effect = [
        [MagicMock()],
        [MagicMock()]
    ]

    result = presence.handle_subscribed(element)

    assert result is None

@pytest.mark.skip
def test_handle_unsubscribed(setup_presence):
    presence, mock_connections, mock_retrieve_roster, _, _ = setup_presence
    element = ET.Element('presence', attrib={'type': 'unsubscribed', 'to': 'user@localhost', 'id': '123'})

    presence._jid = JID('user2@localhost')

    mock_retrieve_roster.side_effect = [
        [(1, 'user2@localhost', '<item jid="user@localhost" subscription="both"/>')]
    ]

    mock_connections.get_buffer.return_value = [MagicMock()]

    result = presence.handle_unsubscribed(element)

    assert result is None

@pytest.mark.skip
def test_handle_unavailable(setup_presence):
    presence, mock_connections, mock_retrieve_roster, _, _ = setup_presence
    element = ET.Element('presence', attrib={'type': 'unavailable', 'from': 'user2@localhost', 'id': '123'})

    presence._jid = JID('user2@localhost')

    mock_retrieve_roster.return_value = [
        (1, 'user@localhost', '<item jid="user2@localhost" subscription="both"/>')
    ]

    mock_connections.get_buffer.return_value = [MagicMock()]

    result = presence.handle_unavailable(element)

    assert result is None

@pytest.mark.skip
def test_feed_handle_initial_presence(setup_presence):
    presence, mock_connections, mock_retrieve_roster, _, _  = setup_presence
    element = ET.Element('presence', attrib={'id': '123'})
    presence._jid = JID('user2@localhost')

    mock_retrieve_roster.return_value = [
        (1, 'user2@localhost', '<item jid="user@localhost" subscription="both"/>')
    ]

    buffer_mock = MagicMock()
    mock_connections.get_buffer.return_value = [buffer_mock]

    result = presence.feed(element)

    assert result is None
    mock_retrieve_roster.assert_called_once()
    mock_connections.get_buffer.assert_called_once()
    buffer_mock[-1].write.assert_called_once()

@pytest.mark.skip
def test_handle_initial_presence(setup_presence):
    presence, mock_connections, mock_retrieve_roster, mock_update, _ = setup_presence
    element = ET.Element('presence', attrib={'id': '123'})
    presence._jid = JID('user@localhost')

    mock_retrieve_roster.return_value = [
        (1, 'user2@localhost', '<item jid="user2@localhost" subscription="both"/>')
    ]

    buffer_mock = MagicMock()
    mock_connections.get_buffer.return_value = [buffer_mock]

    presence.handle_initial_presence(element)

    mock_retrieve_roster.assert_called_once()
    mock_connections.get_buffer.assert_called_once()
    buffer_mock[-1].write.assert_called_once()

if __name__ == "__main__":
    pytest.main()
