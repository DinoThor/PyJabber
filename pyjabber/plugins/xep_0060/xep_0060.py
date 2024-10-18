from xml.etree import ElementTree as ET
from yaml import load, Loader

from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.metadata import Metadata


class PubSub(Plugin):
    def __init__(self):
        self._host = Metadata().host
        self._jid = load(open(Metadata().config_path), Loader=Loader)['items']['Pubsub'].replace('$', self._host)

    def feed(self, element: ET.Element):
        pass


    def discover_nodes(self):
        pass
