import xml.etree.ElementTree as ET
from typing import Any, Dict
from uuid import uuid4
from xml.etree.ElementTree import Element

from pyjabber.features.feature_utils.RosterUtils import create_roster_entry
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.features.feature_utils import RosterUtils as RU
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.stream.JID import JID


class Presence:
    def __init__(self, jid: JID) -> None:
        self._handlers = {
            "subscribe": self.handle_subscribe,
            "subscribed": self.handle_subscribed,
            "unsubscribed": self.handle_unsubscribed,
            "unavailable": self.handle_unavailable
        }
        self._connections = ConnectionManager()
        self._jid = jid

        pending = RU.check_pending_sub(self._jid.bare())
        for p in pending:
            buffer = self._connections.get_buffer(jid)
            for b in buffer:
                b[-1].write(p[-1].encode())

    def feed(self, element: Element, extra: Dict[str, Any] = None):
        if "type" in element.attrib:
            return self._handlers[element.get("type")](element)

        if "to" not in element.attrib:
            return self.handle_initial_presence(element)

        return None

    def handle_subscribe(self, element: ET.Element):
        to = JID(element.attrib["to"])
        pending = RU.check_pending_sub_to(self._jid.bare(), to.bare())

        if pending:
            return

        roster_manager = Roster(self._jid.bare())

        if "from" not in element.attrib:
            element.attrib["from"] = str(self._jid)

        # Handle presence locally
        if to.domain == "localhost":
            roster = RU.retrieve_roster(self._jid.bare())
            buffer = self._connections.get_buffer(to)

            item = [item for item in roster
                    if ET.fromstring(item[2]).attrib["jid"] == to.bare()]

            if not item:
                create_roster_entry(self._jid, to, roster_manager)

                roster = RU.retrieve_roster(self._jid.bare())
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
                RU.store_pending_sub(self._jid.bare(), to.bare(), element)


    def handle_subscribed(self, element: ET.Element):
        to = JID(element.attrib.get("to"))
        bare_jid = JID(self._jid.bare())

        if "from" not in element.attrib:
            element.attrib["from"] = str(self._jid)

        if to.domain == "localhost":
            bufferBob = self._connections.get_buffer(to)
            bufferAlice = self._connections.get_buffer(bare_jid)

            rosterBob = RU.retrieve_roster(to)
            rosterAlice = RU.retrieve_roster(bare_jid)

            if not rosterAlice:
                create_roster_entry(bare_jid, to, Roster(bare_jid))
                rosterAlice = RU.retrieve_roster(bare_jid)

            rosterPushBob = None
            rosterPushAlice = None

            itemBob = [  # Alice appears in Bob's roster
                item
                for item in rosterBob
                if ET.fromstring(item[2]).attrib["jid"] == bare_jid
            ]

            itemAlice = [  # Bob appears in Alice's roster
                item
                for item in rosterAlice
                if ET.fromstring(item[2]).attrib["jid"] == to
            ]

            if itemBob:
                itemBob = itemBob[0]
                ETitemBob = ET.fromstring(itemBob[2])
                newItemBob = ETitemBob.__copy__()

                if ETitemBob.attrib["subscription"] == "none":
                    if "ask" in newItemBob.attrib:
                        newItemBob.attrib.pop("ask")
                        newItemBob.attrib["subscription"] = "to"

                if ETitemBob.attrib["subscription"] == "from":
                    if "ask" in newItemBob.attrib:
                        newItemBob.attrib.pop("ask")
                        newItemBob.attrib["subscription"] = "both"

                rosterPushBob = RU.update(item=newItemBob, id=itemBob[0])

            if itemAlice:
                itemAlice = itemAlice[0]
                ETitemAlice = ET.fromstring(itemAlice[2])
                newItemAlice = ETitemAlice.__copy__()

                if ETitemAlice.attrib["subscription"] == "none":
                    newItemAlice.attrib["subscription"] = "from"

                if ETitemAlice.attrib["subscription"] == "to":
                    newItemAlice.attrib["subscription"] = "both"

                rosterPushAlice = RU.update(item=newItemAlice, id=itemAlice[0])

            for bob in bufferBob:
                res = ET.Element(
                    "presence",
                    attrib={
                        "from": str(bare_jid),
                        "to": str(to),
                        "id": element.attrib.get('id') or str(uuid4()),
                        "type": "subscribed",
                    },
                )

                bob[-1].write(ET.tostring(res))

            if rosterPushBob:
                for bob in bufferBob:
                    res = ET.Element(
                        "iq",
                        attrib={
                            "id": str(uuid4()),
                            "to": bob[0],
                            "type": "set"
                        }
                    )
                    query = ET.Element(
                        "query", attrib={
                            "xmlns": "jabber:iq:roster"})
                    item = ET.fromstring(rosterPushBob)

                    query.append(item)
                    res.append(query)

                    bob[-1].write(ET.tostring(res))

            if rosterPushAlice:
                for alice in bufferAlice:
                    res = ET.Element(
                        "iq",
                        attrib={
                            "id": str(uuid4()),
                            "to": alice[0],
                            "type": "set"
                        }
                    )
                    query = ET.Element(
                        "query", attrib={
                            "xmlns": "jabber:iq:roster"})
                    item = ET.fromstring(rosterPushAlice)

                    query.append(item)
                    res.append(query)

                    alice[-1].write(ET.tostring(res))

    def handle_initial_presence(self, element: ET.Element):
        bare_jid = self._jid.bare()
        roster = RU.retrieve_roster(JID(bare_jid))

        for r in roster:
            item = ET.fromstring(r[-1])
            jid = JID(item.get("jid"))
            buffer = self._connections.get_buffer(jid)
            for b in buffer:
                presence = ET.Element(
                    "presence",
                    attrib={
                        "from": str(self._jid),
                        "to": b[0].bare()})
                b[-1].write(ET.tostring(presence))

    def handle_unsubscribed(self, element: ET.Element):
        to = JID(element.attrib["to"]).bare()
        bare_jid = self._jid.bare()

        if "from" not in element.attrib:
            element.attrib["from"] = str(self._jid)

        # Handle locally
        if to.split("@")[1] == "localhost":
            roster = RU.retrieve_roster(JID(bare_jid))
            buffer = self._connections.get_buffer(JID(to))

            item = [item for item in roster
                    if ET.fromstring(item[2]).attrib["jid"] == to]

            if not item:
                return

            item = item[0]
            ETitem = ET.fromstring(item[2])

            newItem = ETitem.__copy__()

            if ETitem.attrib["subscription"] == "to":
                newItem.attrib["subscription"] = "none"
                RU.update(item=newItem, id=item[0])

            elif ETitem.attrib["subscription"] == "both":
                newItem.attrib["subscription"] = "from"
                RU.update(item=newItem, id=item[0])

            elif "ask" in ETitem.attrib:
                newItem.attrib.pop("ask")
                RU.update(item=newItem, id=item[0])

            id = str(uuid4())

            for b in buffer:
                presence = ET.Element(
                    "presence",
                    attrib={
                        "to": b[0],
                        "from": element.attrib['from'],
                        "id": element.attrib['id'],
                        "type": "unsubscribed"
                    }
                )

                roster_push = ET.Element(
                    "iq",
                    attrib={
                        "id": id,
                        "to": b[0],
                        "type": "set"
                    }
                )

                query = ET.Element("{jabber:iq:roster}query")
                query.append(newItem)
                roster_push.append(query)

                b[-1].write(ET.tostring(presence))
                b[-1].write(ET.tostring(roster_push))

    def handle_unavailable(self, element: ET.Element):
        bare_jid = self._jid.bare()

        if "from" not in element.attrib:
            element.attrib["from"] = str(self._jid)

        roster = RU.retrieve_roster(bare_jid)

        for item in roster:
            to = ET.fromstring(item[-1]).attrib["jid"]

            if to.split("@")[1] == "localhost":
                presence = element.__copy__()

                presence.attrib["to"] = to

                buffer = self._connections.get_buffer(to)
                for b in buffer:
                    b[-1].write(ET.tostring(presence))
