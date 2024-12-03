from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

from pyjabber.features.feature_utils.RosterUtils import create_roster_entry
from pyjabber.stream.JID import JID

@patch('pyjabber.features.feature_utils.RosterUtils.uuid4', return_value="1234-5678-uuid")
def test_create_roster_entry(mock_uuid4):
    # Configuramos el mock para uuid4

    mock_roster_manager = MagicMock()

    jid = JID("user1@localhost")
    to = JID("user2@localhost")

    create_roster_entry(jid, to, mock_roster_manager)

    expected_iq = ET.Element(
        "iq", attrib={"from": str(jid), "id": "1234-5678-uuid", "type": "set"}
    )
    query = ET.Element("{jabber:iq:roster}query")
    item = ET.Element("{jabber:iq:roster}item", attrib={"jid": str(to), "subscription": "none"})
    query.append(item)
    expected_iq.append(query)

    expected_iq_str = ET.tostring(expected_iq).decode()
    actual_iq_str = ET.tostring(mock_roster_manager.feed.call_args[0][1]).decode()

    assert expected_iq_str == actual_iq_str
