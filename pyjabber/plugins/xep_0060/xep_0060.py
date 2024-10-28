import json
from abc import ABC
from contextlib import closing
from typing import List
from xml.etree import ElementTree as ET
from yaml import load, Loader

from pyjabber.metadata import Metadata
from pyjabber.db.database import connection
from pyjabber.utils import Singleton


class PubSub(metaclass=Singleton):
    def __init__(self, db_connection_factory=None):
        super().__init__()
        items = load(open(Metadata().config_path), Loader=Loader)['items']
        service_jid = next((s for s in list(items) if 'pubsub' in s), None)
        if service_jid is None:
            raise Exception  # TODO: Define missing config exception

        self._jid = service_jid
        self._category = items.get('type')
        self._ver = items.get('var')

        self._host = Metadata().host
        self._db_connection_factory = db_connection_factory or connection

        with closing(self._db_connection_factory()) as con:
            res = con.execute("SELECT * FROM pubsub")
            self._data = json.loads(res.fetchall()[0][0])

    def feed(self, jid: str, element: ET.Element):
        pass

    def discover_items(self, element: ET.Element) -> List[tuple]:
        """
            Returns the available nodes at the level specified in the query

            :return: A list of 3-tuples in the format (node, name, type)
        """
        query = element.find('{http://jabber.org/protocol/disco#items}query')
        if query and query.attrib.get('node') is None:  # Query to root
            pass

        else:  # Query to branch/leaf in the nodes tree
            res = []
            for collection in self._data['root'].keys():
                name = self._data[collection].get('name')
                node_type = self._data[collection].get('type')
                res.append((collection, name, node_type))
            return res
