import json
import sqlite3
from contextlib import closing
from enum import Enum
from typing import List, Dict
from xml.etree import ElementTree as ET

from loguru import logger
from yaml import load, Loader

from pyjabber.metadata import Metadata
from pyjabber.db.database import connection
from pyjabber.utils import Singleton, ClarkNotation as CN

class NodeAttrib(Enum):
    NODE = 0
    NAME = 1
    TYPE = 2
    SUBS = 3
    ITEMS = 4

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

        self._nodes = None
        self.update_memory_from_database()

        self._operations = {
            'create': self.create_node,
            'delete': self.delete_node,
        }

    def update_memory_from_database(self):
        with closing(self._db_connection_factory()) as con:
            res = con.execute("SELECT * FROM pubsub")
            self._nodes = res.fetchall()

    def feed(self, jid: str, element: ET.Element):
        try:
            _, tag = CN.deglose(element[0].tag)

            if tag != 'pubsub':
                return # TODO: malformed request

            _, operation = CN.deglose(element[0][0].tag)
            return self._operations[operation](element[0][0])
        except (KeyError, TypeError) as e:
            pass # TODO: Malformed request


    def discover_items(self, element: ET.Element) -> List[tuple]:
        """
        Returns the available nodes at the level specified in the query
        :return: A list of 3-tuples in the format (node, name, type)
        """
        query = element.find('{http://jabber.org/protocol/disco#items}query')
        if query and query.attrib.get('node') is None:  # Query to root
            res = []
            for node in self._nodes:
                _node = node[NodeAttrib.NODE]
                _name = node[NodeAttrib.NAME]
                _type = node[NodeAttrib.TYPE]
                res.append((_node, _name, _type))
            return res

        else:  # Query to branch/leaf in the nodes tree
            pass

    def discover_info(self, element: ET.Element):
        """
            Return the info for a given node
            :return: A 2-tuple in the format of (name, type)
        """
        query = element.find('{http://jabber.org/protocol/disco#info}query')
        query_node = query.attrib.get('node')
        if query is not None and query_node is not None:
            match_node = next((node for node in self._nodes if node[NodeAttrib.NODE] == query_node), None)
            if match_node:
                return match_node[NodeAttrib.NAME], match_node[NodeAttrib.TYPE]

        return None

    def create_node(self, element: ET.Element):
        new_node = element.attrib.get('node')
        if new_node is None:
            pass # TODO: malformed petition

        if [node for node in self._nodes if node[NodeAttrib.NODE.value] == new_node]:
            return # TODO: node already exist with given name

        """
        A new item MUST follow the order described in the NodeAttrib enum
        for correct attribute access
        """
        item = (
            new_node,   # NODE
            None,       # NAME
            'leaf',     # TYPE
            '[]',       # SUBSCRIBERS LIST
            '[]'        # ITEMS LIST
        )

        with closing(self._db_connection_factory()) as con:
            con.execute("INSERT INTO pubsub VALUES (?,?,?,?,?)", item)
            con.commit()

        self.update_memory_from_database()


    def delete_node(self, element: ET.Element):
        del_node = element.attrib.get('node')
        if del_node is None:
            pass  # TODO: malformed petition

        if len([node for node in self._nodes if node[NodeAttrib.NODE.value] == del_node]) == 0:
            return  # TODO: node not exist

        with closing(self._db_connection_factory()) as con:
            con.execute("DELETE FROM pubsub WHERE node = ?", (del_node,))
            con.commit()

        self.update_memory_from_database()

    def subscribe_node(self, element: ET.Element):
        pass

    def unsubscribe_node(self, element: ET.Element):
        pass

    def error_factory(self, element: ET.Element):
        pass
