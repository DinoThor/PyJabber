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

    def feed(self, element: ET.Element, jid: str, extra: dict[str, any] = None):
        if "type" in element.attrib:
            self._jid = jid
            self._handlers[element.attrib["type"]](element)

    def handleSubscribe(self, element: ET.Element):
        to      = element.attrib["to"]
        jid     = self._jid.split("/")[0]
        print(to)
        if to.split("@")[1] == "localhost":
            if "from" not in element.attrib:
                element.attrib["from"] = self._jid

            roster  = self._roster.retriveRoster(jid)
            roster  = list(map(lambda r: ET.fromstring(r[2]), roster))
            item    = [item for item in roster if item.attrib["jid"] == to]
            if item:
                item = item[0]

            if item.attrib["subscription"] in ["to", "both"]:
                return f"<presence from='{element.attrib['to']}' id='{element.attrib['id']}' to='{element.attrib['from']}' type='subscribed'/>".encode()
            
            newItem = item.__copy__()
            newItem.attrib["ask"] = "subscribe"
            
            self._roster.update(jid, item = ET.tostring(newItem), oldItem = ET.tostring(item))

            if "from" not in element.attrib:
                element.attrib["from"] = self._jid

            buffer = self._connections.get_buffer_by_jid(to)
            print(buffer)
            if buffer is not None:
                print(buffer)
                for b in buffer:
                    b.write(
                        f"<presence from='{element.attrib['from']}' id='{element.attrib['id']}' to='{element.attrib['to']}' type='subscribe'/>".encode()
                    )

        return f"<presence from='test@localhost' id='{element.attrib['id']}' to='demo@localhost' type='subscribe'/>"
    
    def handleSubscribed(self):
        pass

    def setSubscription(self, item: ET.Element):
        jid     = self._jid.split("/")[0]
        roster  = self._roster.retriveRoster(jid)
        roster  = list(map(lambda r: ET.fromstring(r[2]), roster))
        item    = [item for item in roster if item.attrib["jid"] == "testing1@localhost"]
        if item and item[0].attrib["subscription"] in ["from", "to", "both"]:
            return True
        return False