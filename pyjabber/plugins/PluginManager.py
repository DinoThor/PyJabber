from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.PluginInterface import Plugin
import pyjabber.stanzas.error.StanzaError as SE
from pyjabber.utils import ClarkNotation as CN

from pyjabber.plugins.xep_0077 import inBandRegistration

import xml.etree.ElementTree as ET

class PluginManager():
    def __init__(self, jid) -> None:
        
        self._jid = jid
        self._plugins: dict[str, Plugin] = {
            'jabber:iq:roster'      : Roster,
            'jabber:iq:register'    : inBandRegistration
        }
        self._activePlugins: dict[str, Plugin] = {}

    def feed(self, element: ET.Element):
        if not element:
            return SE.invalid_xml()
        
        child = element[0]
        tag, _ = CN.deglose(child.tag)
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

      