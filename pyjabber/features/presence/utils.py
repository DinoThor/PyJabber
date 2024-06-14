import xml.etree.ElementTree as ET
from uuid import uuid4
from pyjabber.features.feature_utils import RosterUtils as RU


def create_roster_entry(jid, to, roster_manager):
    iq = ET.Element(
        "iq", attrib={"from": jid, "id": str(uuid4()), "type": "set"}
    )
    query = ET.Element("{jabber:iq:roster}query")
    item = ET.Element("{jabber:iq:roster}item", attrib={"jid": to, "subscription": "none"})
    query.append(item)
    iq.append(query)

    return roster_manager.feed(iq)
