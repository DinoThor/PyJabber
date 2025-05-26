from asyncio import Transport
from itertools import chain
from typing import List, Tuple, Optional
from uuid import uuid4
from xml.etree import ElementTree as ET

from loguru import logger
from sqlalchemy import select, insert, delete, update, and_

from pyjabber import metadata
from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.plugins.xep_0060.enum import NodeAttrib, SubscribersAttrib, Subscription, Affiliation
from pyjabber.plugins.xep_0060.error import ErrorType
from pyjabber.plugins.xep_0060.error import error_response
from pyjabber.stanzas.IQ import IQ
from pyjabber.stanzas.Message import Message
from pyjabber.stanzas.error import StanzaError
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton, ClarkNotation as CN


class PubSub(metaclass=Singleton):
    def __init__(self):
        super().__init__()

        self._connections = ConnectionManager()
        items = metadata.ITEMS
        pubsub_item = next((var for var in items if [var[0] == 'pubsub']), None)
        if pubsub_item is None:
            raise Exception  # TODO: Define missing config exception

        self._jid, self._category, self._var = pubsub_item

        self._host = metadata.HOST

        self._nodes = None
        self._subscribers = None
        self.update_memory_from_database()

        self._operations = {
            'create': self.create_node,
            'delete': self.delete_node,
            'subscribe': self.subscribe,
            'unsubscribe': self.unsubscribe,
            'subscriptions': self.retrieve_subscriptions,
            'items': self.retrieve_items_node,
            'purge': self.purge,
            'publish': self.publish,
            'retract': self.retract
        }

    @staticmethod
    def success_response(element: ET.Element, owner: bool = False) -> Tuple[IQ, ET.Element]:
        iq_res = IQ(
            type_=IQ.TYPE.RESULT,
            from_=metadata.HOST,
            id_=element.attrib.get('id') or str(uuid4())
        )
        if owner:
            xmlns = 'http://jabber.org/protocol/pubsub#owner'
        else:
            xmlns = 'http://jabber.org/protocol/pubsub'

        pubsub = ET.SubElement(iq_res, f'{{{xmlns}}}pubsub')
        return iq_res, pubsub

    def update_memory_from_database(self):
        with DB.connection() as con:
            query = select(Model.Pubsub)
            self._nodes = con.execute(query).fetchall()

            query = select(Model.PubsubSubscribers)
            self._subscribers = con.execute(query).fetchall()

    def feed(self, jid: JID, element: ET.Element):
        try:
            _, tag = CN.deglose(element[0].tag)

            if tag != 'pubsub':
                return StanzaError.invalid_xml()

            _, operation = CN.deglose(element[0][0].tag)
            return self._operations[operation](element, jid)
        except KeyError as e:
            logger.error(f"Pubsub operation not supported: {e}")
            return StanzaError.feature_not_implemented(feature=str(e), namespace="{http://jabber.org/protocol/pubsub}pubsub")

    def discover_items(self, element: ET.Element) -> List[tuple]:
        """
        Returns the available nodes at the level specified in the query
        :return: A list of 3-tuples in the format (node, name, type)
        """
        query = element.find('{http://jabber.org/protocol/disco#items}query')
        if query is None:
            return []
        res = []
        if query.attrib.get('node') is None:  # Query to root
            for node in self._nodes:
                _node = node[NodeAttrib.NODE.value]
                _name = node[NodeAttrib.NAME.value]
                _type = node[NodeAttrib.TYPE.value]
                res.append((_node, _name, _type))
            return res

        else:  # Query to branch/leaf in the nodes tree
            target_node = query.attrib.get('node')
            node_match = [node for node in self._nodes if node[NodeAttrib.NODE.value] == target_node]
            if node_match:
                for node in node_match:
                    _node = node[NodeAttrib.NODE.value]
                    _name = node[NodeAttrib.NAME.value]
                    _type = node[NodeAttrib.TYPE.value]
                    res.append((_node, _name, _type))
            return res

    def discover_info(self, element: ET.Element):
        """
        Return the info for a given node
        :return: A 2-tuple in the format of (name, type)
        """
        query = element.find('{http://jabber.org/protocol/disco#info}query')
        query_node = query.attrib.get('node')
        if query is not None and query_node is not None:
            match_node = [node for node in self._nodes if node[NodeAttrib.NODE.value] == query_node]
            if match_node:
                match_node = match_node.pop()
                return match_node[NodeAttrib.NAME.value], match_node[NodeAttrib.TYPE.value]

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
        if not new_node:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        # Node already exists
        if [node for node in self._nodes if node[NodeAttrib.NODE.value] == new_node]:
            return error_response(element, jid, ErrorType.CONFLICT)

        if config:  #pragma: no cover
            pass  # TODO: create node with given configuration

        """
        A new item MUST follow the order described in the NodeAttrib enum
        for correct attribute access
        """
        item = {
            "node": new_node,
            "owner": jid.user,
            "name": None,
            "type": "leaf",
            "max_items": 1024
        }

        with DB.connection() as con:
            query = insert(Model.Pubsub).values(item)
            con.execute(query)
            con.commit()

        self.update_memory_from_database()

        iq_res, pubsub = PubSub.success_response(element)
        ET.SubElement(pubsub, 'create', attrib={'node': new_node})
        return ET.tostring(iq_res)

    def delete_node(self, element: ET.Element, jid: JID):
        """
        Deletes a specific node in the pubsub service.
        ONLY the owner has the permissions to delete.
        """
        pubsub = element.find('{http://jabber.org/protocol/pubsub#owner}pubsub')
        delete_stanza = pubsub.find('{http://jabber.org/protocol/pubsub#owner}delete')
        del_node = delete_stanza.attrib.get('node')

        if not del_node:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        node_match = [node for node in self._nodes if node[NodeAttrib.NODE.value] == del_node]
        if not node_match:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        node_match = node_match.pop()
        if node_match[NodeAttrib.OWNER.value] != jid.user:
            return error_response(element, jid, ErrorType.FORBIDDEN)

        with DB.connection() as con:
            query = delete(Model.Pubsub).where(Model.Pubsub.c.node == del_node)
            con.execute(query)
            con.commit()

            query = delete(Model.PubsubItems).where(Model.PubsubItems.c.node == del_node)
            con.execute(query)
            con.commit()

        self.update_memory_from_database()
        iq_res, _ = PubSub.success_response(element)
        return ET.tostring(iq_res)

    def retrieve_items_node(self, element: ET.Element, jid: JID):
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        items = pubsub.find('{http://jabber.org/protocol/pubsub}items')
        node = items.attrib.get('node')

        if node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        match_node = [n[NodeAttrib.NODE.value] for n in self._nodes if n[NodeAttrib.NODE.value] == node]
        if not match_node:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        target_node: str = match_node.pop()
        is_owner = any(n[NodeAttrib.NODE.value] == target_node and n[NodeAttrib.OWNER.value] == jid.user for n in self._nodes)

        if not is_owner:

            subscribed = any(s[SubscribersAttrib.JID.value] == jid.user
                                and s[SubscribersAttrib.NODE.value] == target_node
                                and s[SubscribersAttrib.SUBSCRIPTION.value] in [Affiliation.MEMBER, Affiliation.PUBLISHER]
                                for s in self._subscribers
                             )

            if not subscribed:
                return error_response(element, jid, ErrorType.FORBIDDEN)

        with DB.connection() as con:
            query = select(Model.PubsubItems).where(Model.PubsubItems.c.node == target_node)
            res = con.execute(query).fetchall()

        iq_res, pubsub_res = PubSub.success_response(element)
        items_res = ET.SubElement(pubsub_res, '{http://jabber.org/protocol/pubsub}items', attrib={
            "node": target_node
        })

        for i in res:
            item = ET.SubElement(items_res, '{http://jabber.org/protocol/pubsub}item', attrib={
                'id': i[2]
            })
            item.append(ET.fromstring(i[3]))

        return ET.tostring(iq_res)

    def subscribe(self, element: ET.Element, jid: JID):
        """
        Subscribe to a specific node
        The default affiliation will be PUBLISHER
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

        current_state = [
            s for s in self._subscribers
            if s[SubscribersAttrib.JID.value] == jid_request.user and s[SubscribersAttrib.NODE.value] == node
        ]
        if len(current_state) >= 1:
            current_state = current_state.pop()
            if (current_state[SubscribersAttrib.SUBSCRIPTION.value]
               in [Subscription.SUBSCRIBED.value, Subscription.UNCONFIGURED.value]):

                iq_res, pubsub = PubSub.success_response(element)
                subid = current_state[SubscribersAttrib.SUBID.value]
                ET.SubElement(
                    pubsub,
                    'subscription',
                    attrib={
                        'node': target_node[NodeAttrib.NODE.value],
                        'jid': jid_request.bare(),
                        'subid': subid,
                        'subscription': 'subscribed'
                    }
                )
                return ET.tostring(iq_res)

            elif current_state[SubscribersAttrib.SUBSCRIPTION.value] == Subscription.PENDING.value:
                return error_response(element, jid, ErrorType.PENDING_SUBSCRIPTION)

        subid = str(uuid4())

        item = {
            "node": target_node[NodeAttrib.NODE.value],
            "jid": jid_request.user,
            "subid": subid,
            "subscription": Subscription.SUBSCRIBED.value,
            "affiliation": Affiliation.PUBLISHER
        }

        with DB.connection() as con:
            query = insert(Model.PubsubSubscribers).values(item)
            con.execute(query)
            con.commit()

        self.update_memory_from_database()

        iq_res, pubsub = PubSub.success_response(element)
        ET.SubElement(
            pubsub,
            'subscription',
            attrib={
                'node': target_node[NodeAttrib.NODE.value],
                'jid': jid_request.bare(),
                'subid': subid,
                'subscription': 'subscribed'
            }
        )
        return ET.tostring(iq_res)

    def unsubscribe(self, element: ET.Element, jid: JID):
        """
        Unsubscribe to a specific node
        """
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        unsubscribe = pubsub.find('{http://jabber.org/protocol/pubsub}unsubscribe')
        node = unsubscribe.attrib.get('node')
        jid_request = unsubscribe.attrib.get('jid')
        subid = None

        if node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        if jid_request is None:
            return error_response(element, jid, ErrorType.INVALID_JID)

        jid_request = JID(jid_request)
        if jid_request.bare() != jid.bare():
            return error_response(element, jid, ErrorType.INVALID_JID)

        target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node]
        if not target_node:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)
        target_node = target_node.pop()

        number_subscriptions = sum(s[SubscribersAttrib.JID.value] == jid_request.user for s in self._subscribers)

        if number_subscriptions == 0:
            return error_response(element, jid, ErrorType.NOT_SUBSCRIBED)

        if number_subscriptions > 1:
            subid = unsubscribe.attrib.get('subid')
            if subid is None:
                return error_response(element, jid, ErrorType.SUBID_REQUIRED)

            if not any(s[SubscribersAttrib.SUBID.value] == subid for s in self._subscribers):
                return error_response(element, jid, ErrorType.INVALID_SUBID)

            query = delete(Model.PubsubSubscribers).where(
                and_(
                    Model.PubsubSubscribers.c.node == target_node[NodeAttrib.NODE.value],
                    Model.PubsubSubscribers.c.jid == jid_request.user,
                    Model.PubsubSubscribers.c.subid == subid
                )
            )

        else:
            query = delete(Model.PubsubSubscribers).where(
                and_(
                    Model.PubsubSubscribers.c.node == target_node[NodeAttrib.NODE.value],
                    Model.PubsubSubscribers.c.jid == jid_request.user
                )
            )

        with DB.connection() as con:
            con.execute(query)
            con.commit()

        self.update_memory_from_database()

        iq_res, pubsub = PubSub.success_response(element)
        sub = ET.SubElement(
            pubsub,
            'subscription',
            attrib={
                'node': target_node[NodeAttrib.NODE.value],
                'jid': jid_request.bare(),
                'subscription': 'none'
            }
        )
        if subid:
            sub.attrib['subid'] = subid
        return ET.tostring(iq_res)

    def retrieve_subscriptions(self, element: ET.Element, jid: JID):
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        subscriptions = pubsub.find('{http://jabber.org/protocol/pubsub}subscriptions')
        target_node = subscriptions.attrib.get('node')
        from_stanza = element.attrib.get('from')

        if from_stanza is not None and JID(from_stanza).user != jid.user:
            return error_response(element, jid, ErrorType.FORBIDDEN)

        iq_res, pubsub = PubSub.success_response(element)
        subscriptions_res = ET.SubElement(pubsub, '{http://jabber.org/protocol/pubsub}subscriptions')

        if target_node is not None and target_node != '':
            query = select(
                Model.PubsubSubscribers.c.node,
                Model.PubsubSubscribers.c.subscription,
                Model.PubsubSubscribers.c.subid
            ).where(
                and_(
                    Model.PubsubSubscribers.c.jid == str(jid.user),
                    Model.PubsubSubscribers.c.node == target_node
                )
            )
        else:
            query = select(
                Model.PubsubSubscribers.c.node,
                Model.PubsubSubscribers.c.subscription,
                Model.PubsubSubscribers.c.subid
            ).where(Model.PubsubSubscribers.c.jid == str(jid.user))

        with DB.connection() as con:
            res = con.execute(query)
            res = res.fetchall()

        for sub in res:
            ET.SubElement(subscriptions_res, '{http://jabber.org/protocol/pubsub}subscription', attrib={
                'node': sub[0],
                'jid': jid.bare(),
                'subscription': sub[1],
                'subid': sub[2]
            })

        return ET.tostring(iq_res)

    def retrieve_affiliations(self, element: ET.Element, jid: str): #pragma: no cover
        pass

    def purge(self, element: ET.Element, jid: JID):
        pubsub = element.find('{http://jabber.org/protocol/pubsub#owner}pubsub')
        purge = pubsub.find('{http://jabber.org/protocol/pubsub#owner}purge')
        node = purge.attrib.get('node')

        if node is None:
            return error_response(element, jid, ErrorType.NODEID_REQUIRED)

        target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node]
        if len(target_node) == 0:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        target_node = target_node.pop()
        if target_node[NodeAttrib.OWNER.value] != jid.user:
            return error_response(element, jid, ErrorType.FORBIDDEN)

        with DB.connection() as con:
            query = delete(Model.PubsubItems).where(Model.PubsubItems.c.node == node)
            con.execute(query)
            con.commit()

        iq_res, _ = PubSub.success_response(element, True)
        return ET.tostring(iq_res)

    def retract(self, element: ET.Element, jid: JID):
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        retract = pubsub.find('{http://jabber.org/protocol/pubsub}retract')
        node = retract.attrib.get('node')
        item = retract.find('{http://jabber.org/protocol/pubsub}item')
        item_id = item.attrib.get('id') if item is not None else None

        if node is None:
            return error_response(element, jid, ErrorType.NODEID_REQUIRED)

        if item is None or item_id is None:
            return error_response(element, jid, ErrorType.ITEM_REQUIRED)

        target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node]
        if len(target_node) == 0:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)
        target_node = target_node.pop()

        current_sub = any(s for s in self._subscribers
                          if s[SubscribersAttrib.JID.value] == jid.user
                          and s[SubscribersAttrib.AFFILIATION.value] == Affiliation.PUBLISHER
                         )

        if jid.user != target_node[NodeAttrib.OWNER.value] and not current_sub:
            return error_response(element, jid, ErrorType.FORBIDDEN)

        with DB.connection() as con:
            query = delete(Model.PubsubItems).where(
                and_(
                    Model.PubsubItems.c.item_id == item_id,
                    Model.PubsubItems.c.node == node
                )
            )
            con.execute(query)
            con.commit()

        iq_res, pubsub_iq = PubSub.success_response(element)

        self.send_notification(
            node=target_node[NodeAttrib.NODE.value],
            retract=True,
            item_id=item_id,
            payload=None
        )

        iq_res.remove(pubsub_iq)
        return ET.tostring(iq_res)

    def publish(self, element: ET.Element, jid: JID):
        pubsub = element.find('{http://jabber.org/protocol/pubsub}pubsub')
        publish = pubsub.find('{http://jabber.org/protocol/pubsub}publish')
        item = publish.find('{http://jabber.org/protocol/pubsub}item')

        item_id, payload = None, None

        if item is not None:
            item_id = item.attrib.get('id')
            payload = item[0]

        node = publish.attrib.get('node')

        target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node]
        if len(target_node) == 0:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        current_sub = [s for s in self._subscribers if s[SubscribersAttrib.AFFILIATION.value] == jid.user]
        if jid.user != target_node[0][NodeAttrib.OWNER.value] \
            or (current_sub and current_sub[0][SubscribersAttrib.AFFILIATION.value] != Affiliation.PUBLISHER):
            return error_response(element, jid, ErrorType.FORBIDDEN)

        if payload is not None:
            with DB.connection() as con:
                if item_id is not None:
                    query = select(Model.PubsubItems.c.item_id).where(
                        and_(
                            Model.PubsubItems.c.item_id == item_id,
                            Model.PubsubItems.c.node == node
                        )
                    )
                    res = con.execute(query).fetchone()

                    if res:
                        query = update(Model.PubsubItems).where(
                            and_(
                                Model.PubsubItems.c.node == target_node[NodeAttrib.NODE.value],
                                Model.PubsubItems.c.item_id == item_id
                            )
                        ).values(payload=item_id)

                    else:
                        query = insert(Model.PubsubItems).values({
                            "node": target_node[0][NodeAttrib.NODE.value],
                            "publisher": jid.bare(),
                            "item_id": item_id,
                            "payload": ET.tostring(payload)
                        })

                    con.execute(query)
                    con.commit()

                else:
                    item_id = str(uuid4())
                    query = insert(Model.PubsubItems).values({
                        "node": target_node[0][NodeAttrib.NODE.value],
                        "publisher": jid.bare(),
                        "item_id": item_id,
                        "payload": ET.tostring(payload)
                    })
                    con.execute(query)
                    con.commit()

        self.send_notification(node=target_node[0][NodeAttrib.NODE.value], payload=payload)

        iq_res, pubsub = PubSub.success_response(element)
        publish = ET.SubElement(pubsub, 'publish', attrib={'node': node})
        if item_id:
            ET.SubElement(publish, 'item', attrib={'id': item_id})
        return ET.tostring(iq_res)

    def send_notification(self, node: str, payload: Optional[ET.Element], item_id: Optional[str] = None, retract: bool = False):
        receivers = [s for s in self._subscribers
                     if s[SubscribersAttrib.NODE.value] == node
                     and s[SubscribersAttrib.AFFILIATION.value] in [Affiliation.MEMBER, Affiliation.PUBLISHER, Affiliation.OWNER]]

        receivers_jid = [r[1] for r in receivers]
        receivers_buffer = [self._connections.get_buffer(JID(user=r, domain=self._host)) for r in receivers_jid]
        receivers_buffer_single_iterator: List[Tuple[JID, Transport]] = list(chain.from_iterable(receivers_buffer))

        event = ET.Element('event', attrib={'xmlns': 'http://jabber.org/protocol/pubsub#event'})
        items = ET.SubElement(event, 'items', attrib={'node': node})

        if retract:
            retract = ET.SubElement(items, 'retract')
            if item_id:
                retract.attrib['id'] = item_id

        else:
            item = ET.SubElement(items, 'item')
            if item_id:
                item.attrib['id'] = item_id
            if payload:
                item.append(payload)

        for jid, buffer, _ in receivers_buffer_single_iterator:
            message = Message(
                mto=jid.bare(),
                mfrom=self._host,
                id=str(uuid4()),
                mtype=None,
                body=event
            )
            buffer.write(ET.tostring(message))
