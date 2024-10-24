from contextlib import closing
from xml.etree import ElementTree as ET
from yaml import load, Loader

from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.metadata import Metadata
from pyjabber.db.database import connection
from pyjabber.utils import Singleton


class PubSub(Plugin):
    def __init__(self, db_connection_factory=None):
        items = load(open(Metadata().config_path), Loader=Loader)['items']
        service_jid = next((s for s in list(items) if 'pubsub' in s), None)
        if service_jid is None:
            raise Exception  # TODO: Define missing config exception

        self._jid = service_jid
        self._category = items.get('type')
        self._ver = items.get('var')

        self._host = Metadata().host
        self._db_connection_factory = db_connection_factory or connection
        self._data = None


    def feed(self, element: ET.Element):
        pass

    def discover_items(self, element: ET.Element):
        query = element.find('{http://jabber.org/protocol/disco#info}query')
        if query.attrib.get('node') is None:  # Query to root
            with closing(self._db_connection_factory()) as con:
                res = con.execute("SELECT * FROM pubsub")
                self._data = res.fetchall()[0]

        else:  # Query to branch/leaf in the nodes tree
            pass
