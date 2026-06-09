import asyncio
from uuid import uuid4
from xml.etree import ElementTree as ET

import loguru
from sqlalchemy import and_, delete

from pyjabber import AppConfig
from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.plugins.xep_0060.types import (
    Affiliation,
    NodeAttrib,
    SubscribersAttrib,
    Subscription,
)
from pyjabber.plugins.xep_0060.error import ErrorType, error_response
from pyjabber.plugins.xep_0060.PubSubMixin import PubSubMixin
from pyjabber.plugins.xep_0060.utils import success_response
from pyjabber.plugins.xep_0060.types import Node, NodeItem, Subscriber
from pyjabber.stanzas.Message import Message
from pyjabber.stream.JID import JID

ET.register_namespace("", "http://jabber.org/protocol/pubsub#event")


class PubSub(PubSubMixin):
    _nodes: list[Node] = []
    _subscribers: list[Subscriber] = []
    _node_items: dict[str, list[NodeItem]] = {}  # Key: Node id

    _pubsub_metadata = {}

    _pubsub_item = None
    _pubsub_jid = None
    _pubsub_category = None
    _pubsub_var = None

    _operations = {
        "subscribe": "subscribe",
        "unsubscribe": "unsubscribe",
        "subscriptions": "retrieve_subscriptions",
        "items": "retrieve_items_node",
        "publish": "publish",
        # "retract": "retract",
        "create": "create_node",
        "configure": "configure_node",
        "delete": "delete_node",
        "purge": "purge_node",
        "default": "get_default_node_config",
    }

    _lock = asyncio.Lock()

    __slots__ = "_connections"

    def __init__(self):
        self._connections = ConnectionManager()

    async def start(self):
        """
        Initialize the PubSub plugin.
        MUST BE CALLED right after its instantiation.
        """
        await self._update_memory_from_database()

        self._pubsub_metadata["item"] = next(
            (
                (key, item)
                for key, item in AppConfig.app_config.items.items()
                if "pubsub" in key
            ),
            None,
        )

        self._pubsub_metadata["jid"] = self._pubsub_metadata["item"][0].replace(
            "$", AppConfig.app_config.host
        )
        self._pubsub_metadata["category"] = self._pubsub_metadata["item"][1]["category"]
        self._pubsub_metadata["var"] = self._pubsub_metadata["item"][1]["var"]

    async def feed(self, jid: JID, element: ET.Element):
        try:
            operation_function = self._retrieve_operation(jid, element)
            return await operation_function(element, jid)
        except Exception as e:
            loguru.logger.error("PUBSUB: ", e)

    async def create_node(self, element: ET.Element, jid: JID):
        """
        Creates a new node in the pubsub service.
        The owner will be the creator of the node.
        Configuration can be included in the creation with a form in the IQ request.
        """
        pubsub = element.find("{http://jabber.org/protocol/pubsub}pubsub")
        create = pubsub.find("{http://jabber.org/protocol/pubsub}create")
        config = pubsub.find("{http://jabber.org/protocol/pubsub}config")

        new_node = create.attrib.get("node")
        if not new_node:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        # Node already exists
        async with self._lock:
            match_node = next(
                (node for node in self._nodes if node["node"] == new_node), None
            )

        if match_node:
            if match_node["owner"] == jid.bare():
                iq_res, pubsub = success_response(element)
                ET.SubElement(pubsub, "create", attrib={"node": new_node})
                return ET.tostring(iq_res)
            else:
                return error_response(element, jid, ErrorType.CONFLICT)

        if config:  # pragma: no cover
            pass  # TODO: create node with given configuration

        item: Node = {
            "node": new_node,
            "owner": jid.bare(),
            "name": None,
            "type": "leaf",
            "max_items": 1024,
        }

        insert_item = await self._insert_pubsub_node_database(item)
        if insert_item:
            await self._insert_pubsub_node_memory(insert_item)

        iq_res, pubsub = success_response(element)
        ET.SubElement(pubsub, "create", attrib={"node": new_node})
        return ET.tostring(iq_res)

    async def delete_node(self, element: ET.Element, jid: JID):
        """
        Deletes a specific node in the pubsub service.
        ONLY the owner has the permissions to delete.
        """
        pubsub = element.find("{http://jabber.org/protocol/pubsub#owner}pubsub")
        delete = pubsub.find("{http://jabber.org/protocol/pubsub#owner}delete")
        delete_node = delete.attrib.get("node")

        if not delete_node:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        match_node = next(
            (node for node in self._nodes if node["node"] == delete_node), None
        )
        if not match_node:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        if match_node["owner"] != jid.bare():
            return error_response(element, jid, ErrorType.FORBIDDEN)

        await self._delete_pubsub_database(match_node["node"])
        await self._delete_pubsub_memory(match_node["node"])

        iq_res, _ = success_response(element)
        return ET.tostring(iq_res)

    async def retrieve_items_node(self, element: ET.Element, jid: JID):
        """
        Retrieve all items for a specific node
        """
        pubsub = element.find("{http://jabber.org/protocol/pubsub}pubsub")
        items = pubsub.find("{http://jabber.org/protocol/pubsub}items")
        node = items.attrib.get("node")

        if node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        match_node = next((node for node in self._nodes if node["node"] == node), None)
        if not match_node:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        if match_node["owner"] != jid.bare():
            is_subscribed = any(
                s["jid"] == jid.bare()
                and s["subscription"] in [Affiliation.MEMBER, Affiliation.PUBLISHER]
                for s in self._subscribers
            )

            if is_subscribed is False:
                return error_response(element, jid, ErrorType.FORBIDDEN)

        items_list = self._node_items.get(node, [])

        iq_res, pubsub_res = success_response(element)
        items_res = ET.SubElement(
            pubsub_res,
            "{http://jabber.org/protocol/pubsub}items",
            attrib={"node": match_node["node"]},
        )

        for i in items_list:
            item = ET.SubElement(
                items_res,
                "{http://jabber.org/protocol/pubsub}item",
                attrib={"id": i["item_id"]},
            )
            item.append(ET.fromstring(i["payload"]))

        return ET.tostring(iq_res)

    async def subscribe(self, element: ET.Element, jid: JID):
        """
        Subscribe to a specific node
        The default affiliation will be PUBLISHER
        """
        pubsub = element.find("{http://jabber.org/protocol/pubsub}pubsub")
        subscribe = pubsub.find("{http://jabber.org/protocol/pubsub}subscribe")
        node = subscribe.attrib.get("node")
        jid_request = subscribe.attrib.get("jid")

        if node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        if jid_request is None:
            return error_response(element, jid, ErrorType.INVALID_JID)

        jid_request = JID(jid_request)
        if jid_request.bare() != jid.bare():
            return error_response(element, jid, ErrorType.INVALID_JID)

        target_node = next((n["node"] for n in self._nodes if n["node"] == node), None)
        if target_node is None:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        current_state_item = next(
            (
                s
                for s in self._subscribers
                if s["jid"] == jid_request.bare() and s["node"] == target_node
            ),
            None,
        )

        if current_state_item:
            if current_state_item["subscription"] in [
                Subscription.SUBSCRIBED.value,
                Subscription.UNCONFIGURED.value,
            ]:
                iq_res, pubsub = success_response(element)
                ET.SubElement(
                    pubsub,
                    "subscription",
                    attrib={
                        "node": target_node,
                        "jid": jid_request.bare(),
                        "subid": current_state_item["subid"],
                        "subscription": Subscription.SUBSCRIBED.value,
                    },
                )
                return ET.tostring(iq_res)

            elif current_state_item["subscription"] == Subscription.PENDING.value:
                return error_response(element, jid, ErrorType.PENDING_SUBSCRIPTION)

        new_subid = str(uuid4())

        new_item: Subscriber = {
            "node": target_node,
            "jid": jid_request.bare(),
            "subid": new_subid,
            "subscription": Subscription.SUBSCRIBED.value,
            "affiliation": Affiliation.MEMBER,
        }

        subscriber_item = await self._insert_pubsub_sub_database(new_item)
        if subscriber_item:
            await self._insert_pubsub_sub_memory(subscriber_item)

        iq_res, pubsub = success_response(element)
        ET.SubElement(
            pubsub,
            "subscription",
            attrib={
                "node": target_node,
                "jid": jid_request.bare(),
                "subid": new_subid,
                "subscription": "subscribed",
            },
        )
        return ET.tostring(iq_res)

    async def unsubscribe(self, element: ET.Element, jid: JID):
        """
        Unsubscribe to a specific node
        """
        pubsub = element.find("{http://jabber.org/protocol/pubsub}pubsub")
        unsubscribe = pubsub.find("{http://jabber.org/protocol/pubsub}unsubscribe")
        node = unsubscribe.attrib.get("node")
        jid_request = unsubscribe.attrib.get("jid")

        if node is None:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        if jid_request is None:
            return error_response(element, jid, ErrorType.INVALID_JID)

        jid_request = JID(jid_request)
        if jid_request.bare() != jid.bare():
            return error_response(element, jid, ErrorType.INVALID_JID)

        target_node = next((n["node"] for n in self._nodes if n["node"] == node), None)
        if not target_node:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        current_subscription = next(
            (s for s in self._subscribers if s["jid"] == jid_request.bare()), None
        )

        if current_subscription is None:
            return error_response(element, jid, ErrorType.NOT_SUBSCRIBED)

        else:
            sub_item = await self._delete_pubsub_sub_memory(
                current_subscription["subid"]
            )
            if sub_item:
                await self._delete_pubsub_sub_database(sub_item)

        iq_res, pubsub = success_response(element)
        ET.SubElement(
            pubsub,
            "subscription",
            attrib={
                "node": target_node,
                "jid": jid_request.bare(),
                "subscription": "none",
            },
        )

        return ET.tostring(iq_res)

    async def retrieve_subscriptions(self, element: ET.Element, jid: JID):
        pubsub = element.find("{http://jabber.org/protocol/pubsub#owner}pubsub")
        subscriptions = pubsub.find(
            "{http://jabber.org/protocol/pubsub#owner}subscriptions"
        )
        target_node = subscriptions.attrib.get("node", None)

        # subscriptions = await self._get_pubsub_sub_memory(jid, target_node)

        iq_res, pubsub = success_response(element)
        subscriptions_res = ET.SubElement(
            pubsub, "{http://jabber.org/protocol/pubsub}subscriptions"
        )

        for sub in subscriptions:
            ET.SubElement(
                subscriptions_res,
                "{http://jabber.org/protocol/pubsub}subscription",
                attrib={
                    # "node": sub[0],
                    "jid": jid.bare(),
                    "subscription": sub[1],
                    "subid": sub[2],
                },
            )

        return ET.tostring(iq_res)

    def retrieve_affiliations(self, element: ET.Element, jid: str):  # pragma: no cover
        pass

    async def purge(self, element: ET.Element, jid: JID):
        pubsub = element.find("{http://jabber.org/protocol/pubsub#owner}pubsub")
        purge = pubsub.find("{http://jabber.org/protocol/pubsub#owner}purge")
        node = purge.attrib.get("node")

        if node is None:
            return error_response(element, jid, ErrorType.NODEID_REQUIRED)

        target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node]
        if len(target_node) == 0:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        target_node = target_node.pop()
        if target_node[NodeAttrib.OWNER.value] != jid.user:
            return error_response(element, jid, ErrorType.FORBIDDEN)

        async with await DB.connection_async() as con:
            query = delete(Model.PubsubItems).where(Model.PubsubItems.c.node == node)
            await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

        iq_res, _ = success_response(element, True)
        return ET.tostring(iq_res)

    async def retract(self, element: ET.Element, jid: JID):
        pubsub = element.find("{http://jabber.org/protocol/pubsub}pubsub")
        retract = pubsub.find("{http://jabber.org/protocol/pubsub}retract")
        node = retract.attrib.get("node")
        item = retract.find("{http://jabber.org/protocol/pubsub}item")
        item_id = item.attrib.get("id") if item is not None else None

        if node is None:
            return error_response(element, jid, ErrorType.NODEID_REQUIRED)

        if item is None or item_id is None:
            return error_response(element, jid, ErrorType.ITEM_REQUIRED)

        target_node = [n for n in self._nodes if n[NodeAttrib.NODE.value] == node]
        if len(target_node) == 0:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)
        target_node = target_node.pop()

        current_sub = any(
            s
            for s in self._subscribers
            if s[SubscribersAttrib.JID.value] == jid.user
            and s[SubscribersAttrib.AFFILIATION.value] == Affiliation.PUBLISHER
        )

        if jid.user != target_node[NodeAttrib.OWNER.value] and not current_sub:
            return error_response(element, jid, ErrorType.FORBIDDEN)

        async with await DB.connection_async() as con:
            query = delete(Model.PubsubItems).where(
                and_(
                    Model.PubsubItems.c.item_id == item_id,
                    Model.PubsubItems.c.node == node,
                )
            )
            await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

        iq_res, pubsub_iq = success_response(element)

        self.send_notification(
            node=target_node[NodeAttrib.NODE.value],
            retract=True,
            item_id=item_id,
            payload=None,
        )

        iq_res.remove(pubsub_iq)
        return ET.tostring(iq_res)

    async def publish(self, element: ET.Element, jid: JID):
        pubsub = element.find("{http://jabber.org/protocol/pubsub}pubsub")
        publish = pubsub.find("{http://jabber.org/protocol/pubsub}publish")
        item = publish.find("{http://jabber.org/protocol/pubsub}item")

        item_id, payload = None, None

        if item is not None:
            item_id = item.attrib.get("id", None)
            if len(item) > 0:
                payload = item[0]

        node = publish.attrib.get("node", None)
        if node is None:
            return error_response(element, jid, ErrorType.NODEID_REQUIRED)

        target_node = next((n for n in self._nodes if n["node"] == node), None)
        if target_node is None:
            return error_response(element, jid, ErrorType.ITEM_NOT_FOUND)

        current_sub = next(
            (
                s
                for s in self._subscribers
                if s["node"] == node and s["jid"] == jid.bare()
            ),
            None,
        )

        if current_sub is None or current_sub["affiliation"] != Affiliation.PUBLISHER:
            if target_node["owner"] != jid.bare():
                return error_response(element, jid, ErrorType.FORBIDDEN)

        if payload is not None:
            if item_id is not None:
                previous_item = next(
                    (i for i in self._node_items[node] if i["item_id"] == item_id), None
                )
                if previous_item:
                    previous_item["publisher"] = jid.bare()
                    if payload:
                        previous_item["payload"] = ET.tostring(payload)

                    new_item = await self._update_pubsub_item_memory(previous_item)
                    if new_item:
                        await self._insert_pubsub_item_database(new_item)

                else:
                    new_item: NodeItem = {
                        "node": target_node["node"],
                        "publisher": jid.bare(),
                        "item_id": item_id,
                        "payload": ET.tostring(payload),
                    }
                    res_item = await self._insert_pubsub_item_database(new_item)
                    if res_item:
                        await self._insert_pubsub_item_database(res_item)

            else:
                new_item_id = str(uuid4())

                new_item: NodeItem = {
                    "node": target_node["node"],
                    "publisher": jid.bare(),
                    "item_id": new_item_id,
                    "payload": ET.tostring(payload),
                }
                res_item = await self._insert_pubsub_item_database(new_item)
                if res_item:
                    await self._insert_pubsub_item_memory(res_item)

        await self.send_notification(new_item)

        iq_res, pubsub = success_response(element)
        publish = ET.SubElement(pubsub, "publish", attrib={"node": node})
        if item_id:
            ET.SubElement(publish, "item", attrib={"id": item_id})
        return ET.tostring(iq_res)

    async def send_notification(self, item: NodeItem, retract: bool = False):
        async with self._lock:
            receivers_bare_jid = [
                receiver
                for receiver in self._subscribers
                if receiver["node"] == item["node"]
                and receiver["affiliation"]
                in [Affiliation.MEMBER, Affiliation.PUBLISHER, Affiliation.OWNER]
            ]

        event = ET.Element(
            "event", attrib={"xmlns": "http://jabber.org/protocol/pubsub#event"}
        )
        items = ET.SubElement(event, "items", attrib={"node": item["node"]})

        if retract:
            retract = ET.SubElement(items, "retract")
            retract.attrib["id"] = item["item_id"]

        else:
            item_notification = ET.SubElement(items, "item")
            item_notification.attrib["id"] = item["item_id"]
            if item["payload"] is not None:
                item_notification.append(ET.fromstring(item["payload"]))

        for receiver in receivers_bare_jid:
            for client in await self._connections.get_transport(JID(receiver["jid"])):
                message = Message(
                    mto=client.jid.bare(),
                    mfrom=self._pubsub_metadata["jid"],
                    id=str(uuid4()),
                    mtype=None,
                    body=event,
                )
                client.transport.write(ET.tostring(message))
