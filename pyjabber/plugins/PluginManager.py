import xml.etree.ElementTree as ET
from typing import Dict

from pyjabber.plugins.PluginInterface import Plugin

# Plugins
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.xep_0199.xep_0199 import Ping
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.utils import ClarkNotation as CN


class PluginManager():
    def __init__(self, jid) -> None:

        self._jid = jid
        self._plugins: Dict[str, Plugin] = {
            'jabber:iq:roster': Roster,
            'urn:xmpp:ping': Ping
        }
        self._activePlugins: Dict[str, Plugin] = {}

    def feed(self, element: ET.Element):
        try:
            child = element[0]
        except IndexError:
            if element.attrib["type"] == "result":
                return
            else:
                return SE.service_unavaliable()

        tag, _ = CN.deglose(child.tag)

        try:
            plugin = self._activePlugins[tag]  # Plugin already instanced
            return plugin.feed(element)
        except KeyError:
            try:
                # Retrive plugin from list and instance
                plugin = self._plugins[tag]
                self._activePlugins[tag] = plugin(self._jid)
                return self._activePlugins[tag].feed(element)
            except KeyError:
                return SE.service_unavaliable()  # Plugin unavailable
