import xml.etree.ElementTree as ET
import re
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

        self._plugins: Dict[str, object] = {
            'jabber:iq:roster': Roster(),
            'urn:xmpp:ping': Ping(),
            'http://jabber.org/protocol/disco*': Disco(),
            'http://jabber.org/protocol/pubsub*': PubSub()
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
            tag = list(filter(lambda regex: re.search(regex, tag), list(self._plugins.keys())))[-1]
            return self._plugins[tag].feed(self._jid, element)
        except KeyError:
            return SE.service_unavaliable()  # Plugin unavailable
