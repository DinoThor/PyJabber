import json
import sqlite3
from contextlib import closing
from enum import Enum
from typing import List, Dict
from uuid import uuid4
from xml.etree import ElementTree as ET

from loguru import logger
from yaml import load, Loader

from pyjabber.metadata import Metadata
from pyjabber.db.database import connection
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton, ClarkNotation as CN


class NodeAttrib(Enum):
    NODE = 0
    NAME = 1
    TYPE = 2
    OWNER = 3


class Subscription(Enum):
    NONE = 0
    PENDING = 1
    UNCONFIGURED = 2
    SUBSCRIBED = 3


class NodeAccess(Enum):
    OPEN = 0
    PRESENCE = 1
    ROSTER = 2
    AUTHORIZE = 3
    WHITELIST = 4


class Affiliation:
    """
    Privileges for each affiliation identity
    https://xmpp.org/extensions/xep-0060.html#affiliations
    """
    OWNER = ['SUB', 'RET', 'PUB', 'DEL', 'PUR', 'CON', 'DEL']
    PUBLISHER = ['SUB', 'RET', 'PUB', 'DEL', 'PUR']
    PUB_ONLY = ['PUB', 'DEL']
    MEMBER = ['SUB', 'RET']
    NONE = ['SUB']
    OUTCAST = []


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
        self._subscribers = None
        self.update_memory_from_database()

        self._operations = {
            'create': self.create_node,
            'delete': self.delete_node,
            'subscriptions': self.retrieve_subscriptions
        }

    def update_memory_from_database(self):
        with closing(self._db_connection_factory()) as con:
            res = con.execute("SELECT * FROM pubsub")
            self._nodes = res.fetchall()
            res = con.execute("SELECT * FROM pubsubSubscribers")
            self._subscribers = res.fetchall()

    def feed(self, jid: JID, element: ET.Element):
        try:
            _, tag = CN.deglose(element[0].tag)

            if tag != 'pubsub':
                return  # TODO: malformed request

            _, operation = CN.deglose(element[0][0].tag)
            return self._operations[operation](element, jid)
        except (KeyError, TypeError) as e:
            pass  # TODO: Malformed request

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

    def create_node(self, element: ET.Element, jid: JID):
        new_node = element[0][0].attrib.get('node')
        if new_node is None:
            iq_res = IQ(type=IQ.TYPE.ERROR.value, from_=Metadata().host, to=str(jid), id=element.attrib.get('id'))
            auth_error = ET.fromstring(
                "<error type='auth'><not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><nodeid-required "
                "xmlns='http://jabber.org/protocol/pubsub#errors'/></error>")
            iq_res.append(auth_error)
            return ET.tostring(iq_res)

        if [node for node in self._nodes if node[NodeAttrib.NODE.value] == new_node]:
            iq_res = IQ(type=IQ.TYPE.ERROR.value, from_=Metadata().host, to=str(jid), id=element.attrib.get('id'))
            auth_error = ET.fromstring(
                "<error type='auth'><conflict xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>")
            iq_res.append(auth_error)
            return ET.tostring(iq_res)

        """
        A new item MUST follow the order described in the NodeAttrib enum
        for correct attribute access
        """
        item = (
            new_node,  # NODE
            jid.user,  # OWNER
            None,  # NAME
            'leaf',  # TYPE
        )

        with closing(self._db_connection_factory()) as con:
            con.execute("INSERT INTO pubsub VALUES (?,?,?,?)", item)
            con.commit()

        self.update_memory_from_database()

        return ET.tostring(IQ(
            type=IQ.TYPE.RESULT.value,
            from_=Metadata().host,
            to=element.attrib.get('from'),
            id=element.attrib.get('id')
        ))

    def delete_node(self, element: ET.Element, jid: JID):
        del_node = element[0][0].attrib.get('node')
        if del_node is None:
            iq_res = IQ(type=IQ.TYPE.ERROR.value, from_=Metadata().host, to=str(jid), id=element.attrib.get('id'))
            auth_error = ET.fromstring(
                "<error type='auth'><not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><nodeid-required "
                "xmlns='http://jabber.org/protocol/pubsub#errors'/></error>")
            iq_res.append(auth_error)
            return ET.tostring(iq_res)

        try:
            node_match = [node for node in self._nodes if node[NodeAttrib.NODE.value] == del_node][0]
        except IndexError:
            iq_res = IQ(type=IQ.TYPE.ERROR.value, from_=Metadata().host, to=str(jid), id=element.attrib.get('id'))
            auth_error = ET.fromstring(
                "<error type='cancel'><item-not-found xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>")
            iq_res.append(auth_error)
            return ET.tostring(iq_res)

        if node_match[NodeAttrib.OWNER.value] != jid.user:
            iq_res = IQ(type=IQ.TYPE.ERROR.value, from_=Metadata().host, to=str(jid), id=element.attrib.get('id'))
            auth_error = ET.fromstring(
                "<error type='auth'><forbidden xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>")
            iq_res.append(auth_error)
            return ET.tostring(iq_res)

        with closing(self._db_connection_factory()) as con:
            con.execute("DELETE FROM pubsub WHERE node = ?", (del_node,))
            con.commit()

        self.update_memory_from_database()

        return ET.tostring(IQ(
            type=IQ.TYPE.RESULT.value,
            from_=Metadata().host,
            to=element.attrib.get('from'),
            id=element.attrib.get('id')
        ))

    def retrieve_subscriptions(self, element: ET.Element, jid: str):
        target_node = element[0][0].attrib.get('node')
        if target_node:
            pass

        with closing(self._db_connection_factory()) as con:
            res = con.execute("SELECT * FROM pubsubSubscribers WHERE jid = ?", (target_node,))
            res = res.fetchall()

    def retrieve_affiliations(self, element: ET.Element, jid: str):
        pass

    def subscribe_node(self, element: ET.Element, jid: str):
        pass

    def unsubscribe_node(self, element: ET.Element, jid: str):
        pass

    def error_factory(self, element: ET.Element):
        pass
