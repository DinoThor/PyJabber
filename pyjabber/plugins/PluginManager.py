import xml.etree.ElementTree as ET

from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.utils import ClarkNotation as CN

# Plugins
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.xep_0199.xep_0199 import Ping


class PluginManager:
    def __init__(self, jid) -> None:

        self._jid = jid
        self._plugins = {
            'jabber:iq:roster': Roster,
            'urn:xmpp:ping': Ping
        }
        self._activePlugins = {}

    def feed(self, element: ET.Element):
        try:
            child = element[0]
        except IndexError:
            if element.attrib["type"] == "result":
                return

        tag, _ = CN.deglose(child.tag)

        try:
            plugin = self._activePlugins[tag]
            return plugin.feed(element)
        except KeyError:
            try:
                plugin = self._plugins[tag]
                self._activePlugins[tag] = plugin(self._jid)
                return self._activePlugins[tag].feed(element)
            except KeyError:
                return SE.service_unavaliable()
