import xml.etree.ElementTree as ET
import re
from typing import Dict

from pyjabber import metadata
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.JID import JID
from pyjabber.utils import ClarkNotation as CN

# Plugins
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.xep_0199.xep_0199 import Ping
from pyjabber.plugins.xep_0030.xep_0030 import Disco
from pyjabber.plugins.xep_0060.xep_0060 import PubSub


class PluginManager:
    __slots__ = ('_jid', '_plugins')

    def __init__(self, jid: JID) -> None:
        self._jid = jid

        self._plugins: Dict[str, object] = {
            'jabber:iq:roster': Roster(),
            'urn:xmpp:ping': Ping
        }

        if any(p.startswith('http://jabber.org/protocol/disco') for p in metadata.PLUGINS):
            self._plugins['http://jabber.org/protocol/disco*'] = Disco()
        if any(p.startswith('http://jabber.org/protocol/pubsub') for p in metadata.PLUGINS):
            self._plugins['http://jabber.org/protocol/pubsub*'] = PubSub()

    def feed(self, element: ET.Element):
        try:
            child = element[0]
        except IndexError:
            if element.attrib["type"] == "result":
                return  # Safe return. Nothing to process
            else:
                return SE.bad_request()

        ns, tag = CN.deglose(child.tag)

        try:
            ns = list(filter(lambda regex: re.search(regex, ns), list(self._plugins.keys())))[-1]
            return self._plugins[ns].feed(self._jid, element)
        except (KeyError, IndexError):
            return SE.feature_not_implemented(tag, ns)
