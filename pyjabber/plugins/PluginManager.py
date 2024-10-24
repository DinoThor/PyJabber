import xml.etree.ElementTree as ET
from typing import Dict

# Plugins
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.xep_0199.xep_0199 import Ping
from pyjabber.plugins.xep_0030.xep_0030 import Disco
from pyjabber.plugins.xep_0060.xep_0060 import PubSub
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.utils import ClarkNotation as CN


class PluginManager:
    def __init__(self, jid) -> None:
        self._jid = jid

        disco = Disco(self._jid)

        self._plugins: Dict[str, object] = {
            'jabber:iq:roster': Roster(self._jid),
            'urn:xmpp:ping': Ping(self._jid),
            'http://jabber.org/protocol/disco#info': disco,
            'http://jabber.org/protocol/disco#items': disco,
            'http://jabber.org/protocol/pubsub': PubSub(self._jid)
        }

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
            return self._plugins[tag].feed(element)
        except KeyError:
            return SE.service_unavaliable()  # Plugin unavailable
