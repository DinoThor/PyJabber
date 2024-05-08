from pyjabber.features.FeatureInterface import FeatureInterface
from pyjabber.plugins.roster.Roster import Roster
import xml.etree.ElementTree as ET

class Presence(FeatureInterface):
    def __init__(self) -> None:
        self._handlers = {
            "subscribe"     : self.handleSubscribe
        }
        self._roster = Roster()

    def feed(self, element: ET.Element, extra: dict[str, any] = None):
        if "type" in element.attrib:
            self._handlers[element.attrib["type"]](element)

    def handleSubscribe(self, element: ET.Element):
        presence = ET.Element(
            "presence",
            attrib = {
                k: v for k, v in element.attrib.items() 
                if k in ["from", "to", "id"]  
            }
        )
        return f"<presence from='test@localhost' id='{element.attrib['id']}' to='demo@localhost' type='subscribe'/>"
        # jid = element.attrib["to"]
        # jid = jid.split("/")[0]
        # roster = self._roster.retriveRoster(jid)
        # print(roster)