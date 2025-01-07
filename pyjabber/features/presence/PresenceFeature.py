import xml.etree.ElementTree as ET
from typing import Any, Dict
from uuid import uuid4
from xml.etree.ElementTree import Element

from pyjabber.features.feature_utils.RosterUtils import create_roster_entry
from pyjabber.metadata import host
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.features.feature_utils import RosterUtils as RU
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton


class Presence(metaclass=Singleton):
    def __init__(self) -> None:
        self._handlers = {
            "subscribe": self.handle_subscribe,
            "subscribed": self.handle_subscribed,
            "unsubscribed": self.handle_unsubscribed,
            "unavailable": self.handle_unavailable
        }
        self._connections = ConnectionManager()

        pending = RU.check_pending_sub()
        for p in pending:
            buffer = self._connections.get_buffer(JID(p[1]))
            for b in buffer:
                b[-1].write(p[-1].encode())

    def feed(self, jid: JID, element: Element, extra: Dict[str, Any] = None):
        if "type" in element.attrib:
            return self._handlers[element.get("type")](jid, element)

        if "to" not in element.attrib:
            return self.handle_initial_presence(jid, element)

        return None

    def handle_subscribe(self, jid: JID, element: ET.Element):
        to = JID(element.attrib["to"])
        pending = RU.check_pending_sub_to(jid.bare(), to.bare())

        if pending:
            return

        roster_manager = Roster(jid.bare())

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        # Handle presence locally
        if to.domain == "localhost":
            roster = RU.retrieve_roster(jid.bare())
            buffer = self._connections.get_buffer(to)

            item = [item for item in roster
                    if ET.fromstring(item[2]).attrib["jid"] == to.bare()]

            if not item:
                create_roster_entry(jid, to, roster_manager)

                roster = RU.retrieve_roster(jid.bare())
                buffer = self._connections.get_buffer(to)

                item = [item for item in roster
                        if ET.fromstring(item[2]).attrib["jid"] == to.bare()]

            item = item[0]
            ETitem = ET.fromstring(item[2])

            if ETitem.attrib["subscription"] in ["to", "both"]:
                petition = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib.get('to'),
                        "to": element.attrib.get('from'),
                        "id": element.attrib.get('id'),
                        "type": "subscribed"
                    }
                )
                return ET.tostring(petition)

            if "ask" not in ETitem.attrib:
                newItem = ETitem.__copy__()
                newItem.attrib["ask"] = "subscribe"
                RU.update(item=newItem, id=item[0])

            if buffer:
                petition = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib['from'],
                        "to": element.attrib['to'],
                        "id": element.attrib['id'],
                        "type": "subscribe"
                    }
                )
                for b in buffer:
                    b[-1].write(ET.tostring(petition))

            else:
                RU.store_pending_sub(jid.bare(), to.bare(), element)

    def handle_subscribed(self, jid: JID, element: ET.Element):
        to = JID(element.attrib.get("to"))

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        if to.domain == "localhost":
            buffer_bob = self._connections.get_buffer(to)
            buffer_alice = self._connections.get_buffer(JID(jid.bare()))

            roster_bob = RU.retrieve_roster(to.bare())
            roster_alice = RU.retrieve_roster(jid.bare())

            if not roster_alice:
                create_roster_entry(JID(jid.bare()), to, Roster(jid.bare()))
                roster_alice = RU.retrieve_roster(jid.bare())

            roster_push_bob = None
            roster_push_alice = None

            item_bob = [  # Alice appears in Bob's roster
                item
                for item in roster_bob
                if ET.fromstring(item[2]).attrib["jid"] == jid.bare()
            ]

            item_alice = [  # Bob appears in Alice's roster
                item
                for item in roster_alice
                if ET.fromstring(item[2]).attrib["jid"] == to.bare()
            ]

            if item_bob:
                item_bob = item_bob[0]
                et_item_bob = ET.fromstring(item_bob[2])
                new_item_bob = et_item_bob.__copy__()

                if et_item_bob.attrib["subscription"] == "none":
                    if "ask" in new_item_bob.attrib:
                        new_item_bob.attrib.pop("ask")
                        new_item_bob.attrib["subscription"] = "to"

                elif et_item_bob.attrib["subscription"] == "from":
                    if "ask" in new_item_bob.attrib:
                        new_item_bob.attrib.pop("ask")
                        new_item_bob.attrib["subscription"] = "both"

                roster_push_bob = RU.update(item=new_item_bob, id=item_bob[0])

            if item_alice:
                item_alice = item_alice[0]
                et_item_alice = ET.fromstring(item_alice[2])
                new_item_alice = et_item_alice.__copy__()

                if et_item_alice.attrib["subscription"] == "none":
                    new_item_alice.attrib["subscription"] = "from"

                if et_item_alice.attrib["subscription"] == "to":
                    new_item_alice.attrib["subscription"] = "both"

                roster_push_alice = RU.update(item=new_item_alice, id=item_alice[0])

            for bob in buffer_bob:
                res = ET.Element(
                    "presence",
                    attrib={
                        "from": jid.bare(),
                        "to": str(to),
                        "id": element.attrib.get('id') or str(uuid4()),
                        "type": "subscribed",
                    },
                )

                bob[-1].write(ET.tostring(res))

            if roster_push_bob:
                for bob in buffer_bob:
                    res = ET.Element(
                        "iq",
                        attrib={
                            "id": str(uuid4()),
                            "to": str(bob[0]),
                            "type": "set"
                        }
                    )
                    query = ET.Element(
                        "query", attrib={
                            "xmlns": "jabber:iq:roster"})
                    item = ET.fromstring(roster_push_bob)

                    query.append(item)
                    res.append(query)

                    bob[-1].write(ET.tostring(res))

            if roster_push_alice:
                for alice in buffer_alice:
                    res = ET.Element(
                        "iq",
                        attrib={
                            "id": str(uuid4()),
                            "to": str(alice[0]),
                            "type": "set"
                        }
                    )
                    query = ET.Element(
                        "query", attrib={
                            "xmlns": "jabber:iq:roster"})
                    item = ET.fromstring(roster_push_alice)

                    query.append(item)
                    res.append(query)

                    alice[-1].write(ET.tostring(res))

    def handle_initial_presence(self, jid: JID, element: ET.Element):
        # bare_jid = self._jid.bare()
        roster = RU.retrieve_roster(jid.bare())

        for r in roster:
            item = ET.fromstring(r[-1])
            jid = JID(item.get("jid"))
            buffer = self._connections.get_buffer(jid)
            for b in buffer:
                presence = ET.Element(
                    "presence",
                    attrib={
                        "from": str(jid),
                        "to": b[0].bare()})
                b[-1].write(ET.tostring(presence))

    def handle_unsubscribed(self, jid: JID, element: ET.Element):
        to = JID(element.attrib["to"])
        # bare_jid = self._jid.bare()

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        # Handle locally
        if to.bare().split("@")[1] == "localhost":
            roster = RU.retrieve_roster(jid.bare())
            buffer = self._connections.get_buffer(to)

            item = [item for item in roster
                    if ET.fromstring(item[2]).attrib["jid"] == to.bare()]

            if not item:
                return

            item = item[0]
            et_item = ET.fromstring(item[2])

            new_item = et_item.__copy__()

            if et_item.attrib["subscription"] == "to":
                new_item.attrib["subscription"] = "none"
                RU.update(item=new_item, id=item[0])

            elif et_item.attrib["subscription"] == "both":
                new_item.attrib["subscription"] = "from"
                RU.update(item=new_item, id=item[0])

            elif "ask" in et_item.attrib:
                new_item.attrib.pop("ask")
                RU.update(item=new_item, id=item[0])

            id_iq = str(uuid4())

            for b in buffer:
                presence = ET.Element(
                    "presence",
                    attrib={
                        "to": b[0],
                        "from": element.attrib.get('from'),
                        "id": element.attrib.get('id'),
                        "type": "unsubscribed"
                    }
                )

                roster_push = ET.Element(
                    "iq",
                    attrib={
                        "id": id_iq,
                        "to": b[0],
                        "type": "set"
                    }
                )

                query = ET.Element("{jabber:iq:roster}query")
                query.append(new_item)
                roster_push.append(query)

                b[-1].write(ET.tostring(presence))
                b[-1].write(ET.tostring(roster_push))

    def handle_unavailable(self, jid: JID, element: ET.Element):
        # bare_jid = self._jid.bare()

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        roster = RU.retrieve_roster(jid.bare())

        for item in roster:
            to = ET.fromstring(item[-1]).attrib.get('jid')

            if to.split("@")[1] == host.get():
                presence = element.__copy__()

                presence.attrib["to"] = to

                buffer = self._connections.get_buffer(JID(to))
                for b in buffer:
                    b[-1].write(ET.tostring(presence))
