from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

from pyjabber.features.feature_utils.RosterUtils import create_roster_entry


@patch('pyjabber.features.presence.utils.uuid4')
def test_create_roster_entry(mock_uuid):
    # Configuramos el mock para uuid4
    mock_uuid.return_value = "1234-5678-uuid"

    mock_roster_manager = MagicMock()

    jid = "user1@localhost"
    to = "user2@localhost"

    create_roster_entry(jid, to, mock_roster_manager)

    expected_iq = ET.Element(
        "iq", attrib={"from": jid, "id": "1234-5678-uuid", "type": "set"}
    )
    query = ET.Element("{jabber:iq:roster}query")
    item = ET.Element("{jabber:iq:roster}item", attrib={"jid": to, "subscription": "none"})
    query.append(item)
    expected_iq.append(query)

    expected_iq_str = ET.tostring(expected_iq).decode()
    actual_iq_str = ET.tostring(mock_roster_manager.feed.call_args[0][0]).decode()

    assert expected_iq_str == actual_iq_str
