import xml.etree.ElementTree as ET
from typing import Any, Dict
from uuid import uuid4
from xml.etree.ElementTree import Element

from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.features.feature_utils import RosterUtils as RU
from pyjabber.features.FeatureInterface import FeatureInterface
from pyjabber.features.presence.utils import create_roster_entry
from pyjabber.plugins.roster.Roster import Roster


class Presence(FeatureInterface):
    def __init__(self, jid) -> None:
        self._handlers = {
            "subscribe": self.handle_subscribe,
            "subscribed": self.handle_subscribed,
            "unsubscribed": self.handle_unsubscribed,
            "unavailable": self.handle_unavailable
        }
        self._connections = ConnectionManager()
        self._jid = jid
        self._bare_jid = self._jid.split("/")[0]

        pending = RU.check_pending_sub(self._bare_jid)
        for p in pending:
            buffer = self._connections.get_buffer(jid)
            for b in buffer:
                b[-1].write(p[-1].encode())

    def feed(self, element: Element, extra: Dict[str, Any] = None):
        if "type" in element.attrib:
            return self._handlers[element.attrib["type"]](element)

        if "to" not in element.attrib:
            return self.handle_initial_presence(element)

        return None

    def handle_subscribe(self, element: ET.Element):
        to = element.attrib["to"].split("/")[0]

        pending = RU.check_pending_sub_to(self._bare_jid, to)

        if pending:
            return

        roster_manager = Roster(self._bare_jid)

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        # Handle presence locally
        if to.split("@")[1] == "localhost":
            roster = RU.retrieve_roster(self._bare_jid)
            buffer = self._connections.get_buffer(to)

            item = [item for item in roster
                    if ET.fromstring(item[2]).attrib["jid"] == to]

            if not item:
                create_roster_entry(self._bare_jid, to, roster_manager)

                roster = RU.retrieve_roster(self._bare_jid)
                buffer = self._connections.get_buffer(to)

                item = [item for item in roster
                        if ET.fromstring(item[2]).attrib["jid"] == to]

            item = item[0]
            ETitem = ET.fromstring(item[2])

            if ETitem.attrib["subscription"] in ["to", "both"]:
                petition = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib['to'],
                        "to": element.attrib['from'],
                        "id": element.attrib['id'],
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
                RU.store_pending_sub(self._bare_jid, to, element)


    def handle_subscribed(self, element: ET.Element):
        to = element.attrib["to"]
        bare_jid = self._jid.split("/")[0]

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        if to.split("@")[1] == "localhost":
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
                        "from": bare_jid,
                        "to": to,
                        "id": element.attrib["id"],
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
        bare_jid = self._jid.split("/")[0]
        roster = RU.retrieve_roster(bare_jid)

        for r in roster:
            item = ET.fromstring(r[-1])
            jid = item.attrib["jid"]
            buffer = self._connections.get_buffer(jid)
            for b in buffer:
                presence = ET.Element(
                    "presence",
                    attrib={
                        "from": self._jid,
                        "to": b[0].split("/")[0]})
                b[-1].write(ET.tostring(presence))

    def handle_unsubscribed(self, element: ET.Element):
        to = element.attrib["to"].split("/")[0]
        bare_jid = self._jid.split("/")[0]

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        # Handle locally
        if to.split("@")[1] == "localhost":
            roster = RU.retrieve_roster(bare_jid)
            buffer = self._connections.get_buffer(to)

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
        bare_jid = self._jid.split("/")[0]

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        roster = RU.retrieve_roster(bare_jid)

        for item in roster:
            to = ET.fromstring(item[-1]).attrib["jid"]

            if to.split("@")[1] == "localhost":
                presence = element.__copy__()

                presence.attrib["to"] = to

                buffer = self._connections.get_buffer(to)
                for b in buffer:
                    b[-1].write(ET.tostring(presence))
