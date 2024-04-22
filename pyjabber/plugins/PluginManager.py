from plugins.roster.Roster import Roster
from plugins.PluginInterface import Plugin
from utils import ClarkNotation

import xml.etree.ElementTree as ET

class PluginManager():
    def __init__(self, jid) -> None:
        
        self._jid = jid
        self._plugins: dict[str, Plugin] = {
            'jabber:iq:roster'      : Roster,
            # 'jabber:'
        }

    def feed(self, element: ET.Element):
        if not element:
            raise Exception() #TODO: Handle "not child in IQ"
        
        child = element[0]
        tag = child.tag.split("#")[0]

        try:
            plugin = self._plugins[tag]
            handler: Plugin = plugin()
            return handler.feed(self._jid, element)
        except KeyError:
            raise Exception() #TODO: Handle "not suported XEP"

      