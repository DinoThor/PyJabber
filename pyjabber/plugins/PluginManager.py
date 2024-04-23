from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.PluginInterface import Plugin
import pyjabber.stanzas.error.StanzaError as SE

import xml.etree.ElementTree as ET

class PluginManager():
    def __init__(self, jid) -> None:
        
        self._jid = jid
        self._plugins: dict[str, Plugin] = {
            'jabber:iq:roster'      : Roster,
        }
        self._activePlugins: dict[str, Plugin] = {}

    def feed(self, element: ET.Element):
        if not element:
            return SE.invalid_xml()
        
        child = element[0]
        tag = child.tag.split("#")[0]
        print(self._plugins[tag])

        try:
            plugin = self._activePlugins[tag]       #Plugin already instanced
            return plugin.feed(self._jid, element)
        except KeyError:
            try:
                plugin = self._plugins[tag]         #Retrive plugin from list and instance
                self._activePlugins[tag] = plugin()
                return self._activePlugins[tag].feed(self._jid, element)
            except KeyError: 
                return SE.service_unavaliable()     #Plugin unavaliable

      