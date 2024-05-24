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
        if "type" in element.attrib:
            self._jid = jid
            return self._handlers[element.attrib["type"]](element)

        # bare <presence/>
        # ···
        return None

    def handleSubscribe(self, element: ET.Element):
        to       = element.attrib["to"]
        bare_jid = self._jid.split("/")[0]

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        # Handle presence locally
        if to.split("@")[1] == "localhost":
            roster  = self._roster.retriveRoster(bare_jid)
            buffer = self._connections.get_buffer_by_jid(to)

            item = [item for item in roster 
                    if ET.fromstring(item[2]).attrib["jid"] == to]  

            # Petition to a contact present in the roster
            print(buffer)
            if item:
                item    = item[0]
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

                for b in buffer:
                    b.write(ET.tostring(petition))
                    return 

            # Petition to a contact NOT present in the roster
            else:
                error = ET.Element(
                "presence",
                attrib={
                    "from": to,
                    "to": element.attrib["from"],
                    "id": element.attrib["id"],
                    "type": "error",
                },
                )
                error.append(
                    ET.fromstring(
                        SE.not_acceptable(
                            "The contact of the presence request is not registed in the roster"
                        ).decode()
                    )
                )

                return ET.tostring(error)

    def handleSubscribed(self, element: ET.Element):
        to       = element.attrib["to"]
        bare_jid = self._jid.split("/")[0]

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        if to.split("@")[1] == "localhost":
            bufferAlice = self._connections.get_buffer_by_jid(bare_jid)
            bufferBob   = self._connections.get_buffer_by_jid(to)
            print(bufferBob)

            rosterBob = self._roster.retriveRoster(to)
            rosterAlice   = self._roster.retriveRoster(bare_jid)

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

                bob.write(ET.tostring(res))

            if rosterPushBob:
                for bob in bufferBob:
                    res = ET.Element(
                        "iq",
                        attrib = {
                            "id"    : str(uuid4()),
                            "to"    : to,
                            "type"  : "set"
                        }
                    )
                    ET.SubElement(res, ET.fromstring(rosterPushBob))

                    bob.write(ET.tostring(res))

            if rosterPushAlice:
                for alice in bufferAlice:
                    res = ET.Element(
                        "iq",
                        attrib={
                            "id": str(uuid4()),
                            "to": bare_jid,
                            "type": "set",
                        },
                    )
                    ET.SubElement(res, ET.fromstring(rosterPushBob))

                    bob.write(ET.tostring(res))

    def roster_push(item: ET.Element):
        pass
