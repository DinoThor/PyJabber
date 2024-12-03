from asyncio import Transport
from contextlib import closing
from enum import Enum
from itertools import chain
from typing import List, Tuple
from uuid import uuid4
from xml.etree import ElementTree as ET

from loguru import logger
from yaml import load, Loader

from pyjabber.metadata import host, config_path
from pyjabber.db.database import connection
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.plugins.xep_0060.error import ErrorType
from pyjabber.plugins.xep_0060.error import error_response
from pyjabber.stanzas.IQ import IQ
from pyjabber.stanzas.Message import Message
from pyjabber.stanzas.error import StanzaError
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton, ClarkNotation as CN


class NodeAttrib(Enum):
    NODE = 0
    OWNER = 1
    NAME = 2
    TYPE = 3
    MAXITEMS = 4


class SubscribersAttrib(Enum):
    NODE = 0
    JID = 1
    SUBID = 2
    SUBSCRIPTION = 3
    AFFILIATION = 4


class Subscription(Enum):
    NONE = 'none'
    PENDING = 'pending'
    UNCONFIGURED = 'unconfigured'
    SUBSCRIBED = 'subscribed'


class NodeAccess(Enum):
    OPEN = 0
    PRESENCE = 1
    ROSTER = 2
    AUTHORIZE = 3
    WHITELIST = 4


class Affiliation:
    OWNER = 'owner'
    PUBLISHER = 'publisher'
    MEMBER = 'member'
    NONE = 'none'
    OUTCAST = 'outcast'


def success_response(element: ET.Element):
    return IQ(
        type=IQ.TYPE.RESULT.value,
        from_=host.get(),
        to=element.attrib.get('from'),
        id=element.attrib.get('id') or str(uuid4())
    )


class PubSub(metaclass=Singleton):
    def __init__(self, db_connection_factory=None):
        super().__init__()

        self._connections = ConnectionManager()

        items = load(open(config_path.get()), Loader=Loader)['items']
        service_jid = next((s for s in list(items) if 'pubsub' in s), None)
        if service_jid is None:
            raise Exception  # TODO: Define missing config exception

        self._jid = service_jid
        self._category = items.get('type')
        self._ver = items.get('var')

        self._host = host.get()
        self._db_connection_factory = db_connection_factory or connection

        self._nodes = None
        self._subscribers = None
        self.update_memory_from_database()

        self._operations = {
            'create': self.create_node,
            'delete': self.delete_node,
            'subscribe': self.subscribe,
            'unsubscribe': self.unsubscribe,
            'subscriptions': self.retrieve_subscriptions,
            'publish': self.publish
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
                return StanzaError.invalid_xml()

            _, operation = CN.deglose(element[0][0].tag)
            return self._operations[operation](element, jid)
        except (KeyError, TypeError) as e:
            logger.error(e)  # TODO: Malformed request

    def discover_items(self, element: ET.Element) -> List[tuple]:
        """
        Returns the available nodes at the level specified in the query
        :return: A list of 3-tuples in the format (node, name, type)
        """
        query = element.find('{http://jabber.org/protocol/disco#items}query')
        if query is not None and query.attrib.get('node') is None:  # Query to root
            res = []
            for node in self._nodes:
                _node = node[NodeAttrib.NODE.value]
                _name = node[NodeAttrib.NAME.value]
                _type = node[NodeAttrib.TYPE.value]
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
        """
        Creates a new node in the pubsub service.
        The owner will be the creator of the node.
        Configuration can be included in the creation with a form in the IQ request.
        """
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        create = pubsub.find('{http://jabber.org/protocol/pubsub}create')
        config = pubsub.find('{http://jabber.org/protocol/pubsub}config')

        new_node = create.attrib.get('node')
        if new_node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        # Node already exists
        if [node for node in self._nodes if node[NodeAttrib.NODE.value] == new_node]:
            return error_response(element, jid, ErrorType.CONFLICT)

        if config:
            pass # TODO: create node with given configuration

        """
        A new item MUST follow the order described in the NodeAttrib enum
        for correct attribute access
        """
        item = (
            new_node,  # NODE
            jid.user,  # OWNER
            None,  # NAME
            'leaf',  # TYPE
            1024  # MAX ITEMS
        )

        with closing(self._db_connection_factory()) as con:
            con.execute("INSERT INTO pubsub VALUES (?,?,?,?,?)", item)
            con.commit()

        self.update_memory_from_database()
        return ET.tostring(success_response(element))

    def delete_node(self, element: ET.Element, jid: JID):
        """
        Deletes a specific node in the pubsub service.
        ONLY the owner has the permissions to delete.
        """
        del_node = element[0][0].attrib.get('node')
        if del_node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        try:
            node_match = [node for node in self._nodes if node[NodeAttrib.NODE.value] == del_node][0]
        except IndexError:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        if node_match[NodeAttrib.OWNER.value] != jid.user:
            return error_response(element, jid, ErrorType.FORBIDDEN)

        with closing(self._db_connection_factory()) as con:
            con.execute("DELETE FROM pubsub WHERE node = ?", (del_node,))
            con.commit()

        self.update_memory_from_database()
        return ET.tostring(success_response(element))

    def subscribe(self, element: ET.Element, jid: JID):
        """
        Subscribe to a specific node
        The default affiliation will be MEMBER
        """
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        subscribe = pubsub.find('{http://jabber.org/protocol/pubsub}subscribe')
        node = subscribe.attrib.get('node')
        jid_request = subscribe.attrib.get('jid')

        if node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        if jid_request is None:
            return error_response(element, jid, ErrorType.INVALID_JID)

        jid_request = JID(jid_request)
        if jid_request.bare() != jid.bare():
            return error_response(element, jid, ErrorType.INVALID_JID)

        try:
            target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node][0]
        except IndexError:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        current_state = [s for s in self._subscribers if s[SubscribersAttrib.JID.value] == jid_request.user]
        if len(current_state) >= 1:
            current_state = current_state[0]
            if current_state[SubscribersAttrib.SUBSCRIPTION.value] in [Subscription.SUBSCRIBED.value, Subscription.UNCONFIGURED.value]:
                return ET.tostring(success_response(element))
            elif current_state[SubscribersAttrib.SUBSCRIPTION.value] == Subscription.PENDING.value:
                return error_response(element, jid, ErrorType.PENDING_SUBSCRIPTION)

        subid = str(uuid4())

        item = (
            target_node[NodeAttrib.NODE.value],
            jid_request.user,
            subid,
            Subscription.SUBSCRIBED.value,
            Affiliation.MEMBER
        )

        with closing(self._db_connection_factory()) as con:
            con.execute("INSERT INTO pubsubSubscribers VALUES (?,?,?,?,?)", item)
            con.commit()

        self.update_memory_from_database()
        res = success_response(element)
        ET.SubElement(
            res,
            'subscription',
            attrib={
                'node': target_node[NodeAttrib.NODE.value],
                'jid': jid_request.bare(),
                'subid': subid,
                'subscription': 'subscribed'
            }
        )
        return ET.tostring(res)

    def unsubscribe(self, element: ET.Element, jid: JID):
        """
        Unsubscribe to a specific node
        """
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        unsubscribe = pubsub.find('{http://jabber.org/protocol/pubsub}unsubscribe')
        node = unsubscribe.attrib.get('node')
        jid_request = unsubscribe.attrib.get('jid')
        subid = unsubscribe.attrib.get('subid')

        if node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        if jid_request is None:
            return error_response(element, jid, ErrorType.INVALID_JID)

        jid_request = JID(jid_request)
        if jid_request.bare() != jid.bare():
            return error_response(element, jid, ErrorType.INVALID_JID)

        try:
            target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node][0]
        except KeyError:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        current_state = [s for s in self._subscribers if s[SubscribersAttrib.JID.value] == jid_request.user]

        if len(current_state) == 0:
            return error_response(element, jid, ErrorType.NOT_SUBSCRIBED)

        if len(current_state) > 1:
            if subid is None:
                return error_response(element, jid, ErrorType.SUBID_REQUIRED)

            if len([s for s in self._subscribers if s[SubscribersAttrib.SUBID.value] == subid]) == 0:
                return error_response(element, jid, ErrorType.INVALID_SUBID)

            query = "DELETE FROM pubsubSubscribers WHERE node = ? AND jid = ? AND subid = ?"
            item = (target_node[NodeAttrib.NODE.value], jid_request.user, subid)

        else:
            query = "DELETE FROM pubsubSubscribers WHERE node = ? AND jid = ?"
            item = (target_node[NodeAttrib.NODE.value], jid_request.user)

        with closing(self._db_connection_factory()) as con:
            con.execute(query, item)
            con.commit()

        self.update_memory_from_database()
        res = success_response(element)
        sub = ET.SubElement(
            res,
            'subscription',
            attrib={
                'node': target_node[NodeAttrib.NODE.value],
                'jid': jid_request.bare(),
                'subscription': 'none'
            }
        )
        if subid: sub.attrib['subid'] = subid
        return ET.tostring(res)

    def retrieve_subscriptions(self, element: ET.Element, jid: JID):
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub') or element.find('{http://jabber.org/protocol/pubsub#owner}pubsub')
        subscriptions = pubsub.find('{http://jabber.org/protocol/pubsub}subscriptions') or pubsub.find('{http://jabber.org/protocol/pubsub#owner}subscriptions')
        target_node = subscriptions.attrib.get('node')
        from_stanza = element.attrib.get('from')

        if from_stanza is not None and JID(from_stanza).user != jid.user:
            return error_response(element, jid, ErrorType.FORBIDDEN)

        iq_res = success_response(element)
        pubsub_res = ET.SubElement(iq_res, 'pubsub' ,attrib={'xmlns': 'http://jabber.org/protocol/pubsub'})
        subscriptions_res = ET.SubElement(pubsub_res, 'subscriptions')

        if target_node is not None and target_node != '':
            query = "SELECT node, subscription, subid FROM pubsubSubscribers WHERE jid = ? AND node = ?"
            item = (str(jid.user), target_node)
        else:
            query = "SELECT node, subscription, subid FROM pubsubSubscribers WHERE jid = ?"
            item = (str(jid.user),)

        with closing(self._db_connection_factory()) as con:
            res = con.execute(query, item)
            res = res.fetchall()

        for sub in res:
            ET.SubElement(subscriptions_res, 'subscription', attrib={
                'node': sub[0],
                'jid': jid.bare(),
                'subscription': sub[1],
                'subid': sub[2]
            })

        return ET.tostring(iq_res)

    def retrieve_affiliations(self, element: ET.Element, jid: str):
        pass

    def publish(self, element: ET.Element, jid: JID):
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        publish = pubsub.find('{http://jabber.org/protocol/pubsub}publish')
        item = publish.find('{http://jabber.org/protocol/pubsub}item')
        payload = item[0]
        node = publish.attrib.get('node')

        if len(item) > 1:
            return error_response(element, jid, ErrorType.INVALID_PAYLOAD)

        target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node]
        if len(target_node) == 0:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        current_sub = [s for s in self._subscribers if s[SubscribersAttrib.AFFILIATION.value] == jid.user]
        if jid.user != target_node[0][NodeAttrib.OWNER.value]\
            or (current_sub and current_sub[0][SubscribersAttrib.AFFILIATION.value] != Affiliation.MEMBER):
            return error_response(element, jid, ErrorType.FORBIDDEN)

        item_id = item.attrib.get('id')

        with closing(self._db_connection_factory()) as con:
            if item_id is not None:
                res = con.execute("SELECT itemid FROM pubsubItems WHERE itemid = ?", item_id)
                if res.fetchone():
                    con.execute("UPDATE pubsubItems "
                                "SET payload = ? "
                                "WHERE node = ? AND itemid = ?",
                                (target_node[NodeAttrib.NODE.value], item_id, ET.tostring(payload)))

            else:
                item_id = str(uuid4())
                con.execute("INSERT INTO pubsubItems VALUES (?,?,?)",
                            (target_node[0][NodeAttrib.NODE.value], item_id, ET.tostring(payload)))
                con.commit()

        self.send_notification(target_node[0][NodeAttrib.NODE.value], payload)

        res = success_response(element)
        pub = ET.SubElement(res, 'pubsub', attrib={'xmlns': 'http://jabber.org/protocol/pubsub'})
        ET.SubElement(pub, 'publish', attrib={'node': 'node'})
        return ET.tostring(res)

    def send_notification(self, node: str, payload: ET.Element, item_id: str = None):
        receivers = [s for s in self._subscribers
         if s[SubscribersAttrib.NODE.value] == node
         and s[SubscribersAttrib.AFFILIATION.value] == Affiliation.MEMBER]

        receivers_jid = [r[1] for r in receivers]
        receivers_buffer = [self._connections.get_buffer(JID(user=r, domain=self._host)) for r in receivers_jid]
        receivers_buffer_single_iterator: List[Tuple[JID, Transport]] = list(chain.from_iterable(receivers_buffer))

        event = ET.Element('event', attrib={'xmlns': 'http://jabber.org/protocol/pubsub#event'})
        items = ET.SubElement(event, 'item')
        if item_id: items.attrib['id'] = item_id
        items.append(payload)

        for jid, buffer in receivers_buffer_single_iterator:
            message = Message(
                mto=jid.bare(),
                mfrom=self._host,
                id=str(uuid4()),
                mtype=None,
                body=event
            )
            buffer.write(ET.tostring(message))


