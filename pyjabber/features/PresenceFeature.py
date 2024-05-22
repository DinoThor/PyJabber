import sys
from pyjabber.features.FeatureInterface import FeatureInterface
from pyjabber.network.ConnectionsManager import ConectionsManager
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

        self._counter = 0

    def feed(self, element: ET.Element, jid: str, extra: dict[str, any] = None):
        if "type" in element.attrib:
            self._jid = jid
            self._handlers[element.attrib["type"]](element)

    def handleSubscribe(self, element: ET.Element):
        self._counter += 1
        if self._counter > 10:
            return
        to      = element.attrib["to"]
        jid     = self._jid.split("/")[0]

        if "from" not in element.attrib:
            element.attrib["from"] = self._jid

        if to.split("@")[1] == "localhost":
            roster  = self._roster.retriveRoster(jid)

            if to.split("@")[0] == jid:
                # item = [item for item in roster 
                #         if ET.fromstring(item[2]).attrib["jid"] == from_]
                
                # if item:
                #     print(item)
                pass

            buffer = self._connections.get_buffer_by_jid(to)

            item = [item for item in roster 
                    if ET.fromstring(item[2]).attrib["jid"] == to]

            if item:
                item    = item[0]
                ETitem  = ET.fromstring(item[2])

                if ETitem.attrib["subscription"] in ["from", "both"]:
                    petition = ET.Element(
                        "presence",
                        attrib = {
                            "from"  : element.attrib['to'],
                            "to"    : element.attrib['from'],
                            "id"    : element.attrib['id'],
                            "type"  : "subscribed"
                        }
                    )
                    for b in buffer:
                        data = ET.tostring(petition)
                        b.write(data)

                newItem = ETitem.__copy__()
                newItem.attrib["subscription"] = "from"
            
                if "ask" not in ETitem.attrib:
                    newItem.attrib["ask"] = "subscribe"
                    
                self._roster.update(item = ET.tostring(newItem), id = item[0])
            

            if buffer:
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
                    data = ET.tostring(petition)
                    b.write(data)
                    # b.write(
                    #     f"<presence from='{element.attrib['from']}' id='{element.attrib['id']}' to='{element.attrib['to']}' type='subscribe'/>".encode()
                    # )

        return f"<presence from='test@localhost' id='{element.attrib['id']}' to='demo@localhost' type='subscribe'/>"
    
    def handleSubscribed(self, element: ET.Element):
        to      = element.attrib["to"]
        jid     = self._jid.split("/")[0]

        if to.split("@")[1] == "localhost":
            if "from" not in element.attrib:
                element.attrib["from"] = self._jid

            buffer = self._connections.get_buffer_by_jid(to)

            roster  = self._roster.retriveRoster(jid)
            item    = [item for item in roster 
                       if ET.fromstring(item[2]).attrib["jid"] == to]

            if item:
                item    = item[0]
                ETitem  = ET.fromstring(item[2])

                if ETitem.attrib["subscription"] in ["to", "both"]:
                    res = ET.Element(
                        "presence",
                        attrib = {
                            "from"  : element.attrib['to'],
                            "to"    : element.attrib['from'],
                            "id"    : element.attrib['id'],
                            "type"  : "subscribed"
                        }
                    )
                    return ET.tostring(res)
                
                newItem = ETitem.__copy__()

                if ETitem.attrib["subscription"] in ["from"]:
                    newItem.attrib["subscription"] = "both"

                if ETitem.attrib["subscription"] in ["none"]:
                    newItem.attrib["subscription"] = "to"
            
                if "ask" in ETitem.attrib:
                    newItem = ETitem.__copy__()
                    newItem.attrib.pop("ask")
                    
                self._roster.update(item = ET.tostring(newItem), id = item[0])                

    def setSubscription(self, item: ET.Element):
        jid     = self._jid.split("/")[0]
        roster  = self._roster.retriveRoster(jid)
        roster  = list(map(lambda r: ET.fromstring(r[2]), roster))
        item    = [item for item in roster if item.attrib["jid"] == "testing1@localhost"]
        if item and item[0].attrib["subscription"] in ["from", "to", "both"]:
            return True
        return False