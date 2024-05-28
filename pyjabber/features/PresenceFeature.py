from uuid import uuid4
from pyjabber.features.FeatureInterface import FeatureInterface
from pyjabber.network.ConnectionsManager import ConectionsManager
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.plugins.roster.Roster import Roster

import xml.etree.ElementTree as ET


class Presence(FeatureInterface):
    def __init__(self) -> None:
        self._handlers = {
            "subscribe"     : self.handleSubscribe,
            "subscribed"    : self.handleSubscribed,
            "unsubscribed"  : None
        }
        self._roster        = Roster()
        self._connections   = ConectionsManager()
        self._jid           = None

    def feed(self, element: ET.Element, jid: str, extra: dict[str, any] = None):
        self._jid = jid

        if "type" in element.attrib:
            return self._handlers[element.attrib["type"]](element)

        if "to" not in element.attrib:
            return self.handleInitialPresence(element)

        return None

    def handleSubscribe(self, element: ET.Element):
        to       = element.attrib["to"].split("/")[0]
        bare_jid = self._jid.split("/")[0]

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        # Handle presence locally
        if to.split("@")[1] == "localhost":
            roster  = self._roster.retriveRoster(bare_jid)
            buffer = self._connections.get_buffer_by_jid(to)

            item = [item for item in roster 
                    if ET.fromstring(item[2]).attrib["jid"] == to]  

            if not item:
                iq = ET.Element(
                    "iq", attrib={"from": self._jid, "id": str(uuid4()), "type": "set"}
                )
                query = ET.Element("{jabber:iq:roster}query")
                item = ET.Element("{jabber:iq:roster}item", attrib={"jid": to, "subscription": "none"})
                query.append(item)
                iq.append(query)

                self._roster.feed(bare_jid, iq)

                roster  = self._roster.retriveRoster(bare_jid)
                buffer = self._connections.get_buffer_by_jid(to)

                item = [item for item in roster 
                        if ET.fromstring(item[2]).attrib["jid"] == to]

            item = item[0]
            ETitem  = ET.fromstring(item[2])

            if ETitem.attrib["subscription"] in ["to", "both"]:
                petition = ET.Element(
                    "presence",
                    attrib = {
                        "from"  : element.attrib['to'],
                        "to"    : element.attrib['from'],
                        "id"    : element.attrib['id'],
                        "type"  : "subscribed"
                    }
                )
                return ET.tostring(petition)

            if "ask" not in ETitem.attrib:
                newItem = ETitem.__copy__()
                newItem.attrib["ask"] = "subscribe"
                print(self._roster.update(item = newItem, id = item[0]))

            petition = ET.Element(
                "presence",
                attrib = {
                    "from"  : element.attrib['from'],
                    "to"    : element.attrib['to'],
                    "id"    : element.attrib['id'],
                    "type"  : "subscribe"
                }
            )
            print(buffer)
            for b in buffer:
                print(b[-1])
                b[-1].write(ET.tostring(petition))
                return 
            
    def handleSubscribed(self, element: ET.Element):
        to       = element.attrib["to"]
        bare_jid = self._jid.split("/")[0]

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        if to.split("@")[1] == "localhost":
            bufferBob   = self._connections.get_buffer_by_jid(to)
            bufferAlice   = self._connections.get_buffer_by_jid(bare_jid)

            rosterBob = self._roster.retriveRoster(to)
            rosterAlice   = self._roster.retriveRoster(bare_jid)

            rosterPushBob = None
            rosterPushAlice = None

            itemBob = [ # Alice appears in Bob's roster
                item
                for item in rosterBob
                if ET.fromstring(item[2]).attrib["jid"] == bare_jid 
            ]

            itemAlice = [ # Bob appears in Alice's roster 
                item
                for item in rosterAlice
                if ET.fromstring(item[2]).attrib["jid"] == to 
            ]

            if itemBob:
                itemBob    = itemBob[0]
                ETitemBob  = ET.fromstring(itemBob[2])
                newItemBob = ETitemBob.__copy__()

                if ETitemBob.attrib["subscription"] == "none":
                    if "ask" in newItemBob.attrib:
                        newItemBob.attrib.pop("ask")
                        newItemBob.attrib["subscription"] = "to"

                if ETitemBob.attrib["subscription"] == "from":
                    if "ask" in newItemBob.attrib:
                        newItemBob.attrib.pop("ask")
                        newItemBob.attrib["subscription"] = "both"

                rosterPushBob = self._roster.update(item = newItemBob, id = itemBob[0])

            if itemAlice:
                itemAlice    = itemAlice[0]
                ETitemAlice  = ET.fromstring(itemAlice[2])
                newItemAlice = ETitemAlice.__copy__()

                if ETitemAlice.attrib["subscription"] == "none":
                    newItemAlice.attrib["subscription"] = "from"

                if ETitemAlice.attrib["subscription"] == "to":
                    newItemAlice.attrib["subscription"] = "both"

                rosterPushAlice = self._roster.update(item = newItemAlice, id = itemAlice[0])

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
                        attrib = {
                            "id"    : str(uuid4()),
                            "to"    : bob[0],
                            "type"  : "set"
                        }
                    )
                    query = ET.Element("query", attrib={"xmlns": "jabber:iq:roster"})
                    item = ET.fromstring(rosterPushBob)

                    query.append(item)
                    res.append(query)

                    bob[-1].write(ET.tostring(res))

            if rosterPushAlice:
                for alice in bufferAlice:
                    res = ET.Element(
                        "iq",
                        attrib = {
                            "id"    : str(uuid4()),
                            "to"    : alice[0],
                            "type"  : "set"
                        }
                    )
                    query = ET.Element("query", attrib={"xmlns": "jabber:iq:roster"})
                    item = ET.fromstring(rosterPushAlice)

                    query.append(item)
                    res.append(query)

                    bob[-1].write(ET.tostring(res))

    def handleInitialPresence(self, element: ET.Element):
        bare_jid = self._jid.split("/")[0]
        roster = self._roster.retriveRoster(bare_jid)

        print(self._jid, bare_jid)

        presence = ET.Element("presence", attrib={"from": self._jid})

        for r in roster:
            item    = ET.fromstring(r[-1])
            jid     = item.attrib["jid"]
            buffer  = self._connections.get_buffer_by_jid(jid)
            for b in buffer:
                presence = ET.Element("presence", attrib={"from": self._jid, "to": b[0].split("/")[0]})
                b[-1].write(ET.tostring(presence))

        return
