from typing import TYPE_CHECKING, List, Union
from xml.etree import ElementTree as ET

from sqlalchemy import and_, delete, insert, select, update

from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.plugins.xep_0060.error import ErrorType, error_response
from pyjabber.plugins.xep_0060.types import Node, NodeItem, Subscriber
from pyjabber.stream.JID import JID
from pyjabber.utils import ClarkNotation as CN

if TYPE_CHECKING:
    from pyjabber.plugins.xep_0060.xep_0060 import PubSub

    BaseClass = PubSub
else:
    BaseClass = object


class PubSubMixin(BaseClass):
    async def _update_memory_from_database(self):
        """
        Initialize the PubSub shared memory with the node and subscriptions information.
        This method is intended to be used ONLY AND ONCE in the configuration and
        initialization of the server. Posterior executions may result in the lost of
        consistency in the current execution and future ones.
        """
        async with await DB.connection_async() as con:
            async with self._lock:
                query = select(Model.Pubsub)
                res = await con.execute(query)
                self._nodes.clear()
                self._nodes.extend(
                    [
                        Node(
                            node=row.node,
                            owner=row.owner,
                            name=row.name,
                            type=row.type,
                            max_items=row.max_items,
                        )
                        for row in res.all()
                    ]
                )

                query = select(Model.PubsubSubscribers)
                res = await con.execute(query)
                self._subscribers.clear()
                self._subscribers.extend(
                    [
                        Subscriber(
                            node=row.node,
                            jid=row.jid,
                            subid=row.subid,
                            subscription=row.subscription,
                            affiliation=row.affiliation,
                        )
                        for row in res.all()
                    ]
                )

    ###################################
    ############### NODE ##############
    ###################################

    async def _insert_pubsub_node_memory(self, item: Node) -> Union[Node, None]:
        """
        Inserts a new node in the PubSub memory.
        If an item with the node already exists, it will not overwrite it.
        """
        async with self._lock:
            already_present = any(n["node"] == item["node"] for n in self._nodes)
            if already_present:
                return None

            self._nodes.append(item)
            return item

    async def _update_pubsub_node_memory(self, item: Node) -> Union[Node, None]:
        """
        Updates an existing node in the PubSub memory.
        If an item with the node already exists, it will overwrite it.
        """
        async with self._lock:
            index = next(
                (i for i, n in enumerate(self._nodes) if n["node"] == item["node"]),
                None,
            )
            if index is None:
                return None

            self._nodes[index] = item
            return item

    async def _delete_pubsub_node_memory(self, node: str) -> Union[Node, None]:
        """
        Deletes node in the PubSub memory.
        If the node is not present, it will return None.
        """
        async with self._lock:
            index, item = next(
                ((i, n) for i, n in enumerate(self._nodes) if n["node"] == node), None
            )
            if index is None:
                return None

            self._nodes.pop(index)
            return item

    @staticmethod
    async def _insert_pubsub_node_database(item: Node) -> Union[Node, None]:
        async with await DB.connection_async() as con:
            query = (
                insert(Model.Pubsub)
                .values(
                    {
                        "node": item["node"],
                        "owner": item["owner"],
                        "name": item["name"],
                        "type": item["type"],
                        "max_items": item["max_items"],
                    }
                )
                .returning(Model.Pubsub)
            )
            res = await con.execute(query)
            await con.commit()
            row = res.first()

            if row is not None:
                return Node(**row._asdict())
            return None

    @staticmethod
    async def _update_pubsub_node_database(item: Node) -> Union[Node, None]:
        async with await DB.connection_async() as con:
            query = (
                update(Model.Pubsub)
                .values(
                    {
                        "node": item["node"],
                        "owner": item["owner"],
                        "name": item["name"],
                        "type": item["type"],
                        "max_items": item["max_items"],
                    }
                )
                .returning(Model.Pubsub)
            )
            res = await con.execute(query)
            row = res.first()

            if row is not None:
                return Node(**row._asdict())
            else:
                return None

    @staticmethod
    async def _delete_pubsub_node_database(node: str) -> Union[Node, None]:
        async with await DB.connection_async() as con:
            query_items = delete(Model.PubsubItems).where(
                Model.PubsubItems.c.node == node
            )
            await con.execute(query_items)

            query = (
                delete(Model.Pubsub)
                .where(Model.Pubsub.c.node == node)
                .returning(Model.Pubsub)
            )
            res = await con.execute(query)
            row = res.first()

            if row is not None:
                return Node(**row._asdict())
            else:
                return None

    ###################################
    ############### SUBS ##############
    ###################################

    async def _insert_pubsub_sub_memory(self, item: Node) -> Union[Node, None]:
        async with self._lock:
            node_match = next(
                (n for n in self._subscribers if n["node"] == item["node"]), None
            )
            if node_match:
                return None

            self._subscribers.append(item)
            return item

    async def _update_pubsub_sub_memory(
        self, item: Subscriber
    ) -> Union[Subscriber, None]:
        async with self._lock:
            index_match, node_match = next(
                (
                    n
                    for n in self._subscribers
                    if n["node"] == item["node"] and n["jid"] == item["jid"]
                ),
                None,
            )
            if node_match:
                self._subscribers[index_match] = item
                return item

            return None

    async def _delete_pubsub_sub_memory(
        self, node: str, jid: JID, subid: Union[str, None] = None
    ) -> Union[Subscriber, None]:
        async with self._lock:
            if subid:
                sub_index, sub_item = next(
                    (
                        (i, v)
                        for i, v in enumerate(self._subscribers)
                        if v["subid"] == subid
                    ),
                    None,
                )
            else:
                sub_index, sub_item = next(
                    (
                        (i, v)
                        for i, v in enumerate(self._subscribers)
                        if v["node"] == node and v["jid"] == jid.bare()
                    ),
                    None,
                )

            if not sub_index:
                return None

            self._subscribers.pop(sub_index)
            return sub_item

    @staticmethod
    async def _insert_pubsub_sub_database(
        subscriber: Subscriber,
    ) -> Union[Subscriber, None]:
        async with await DB.connection_async() as con:
            query = (
                insert(Model.PubsubSubscribers)
                .values(
                    {
                        "node": subscriber["node"],
                        "jid": subscriber["jid"],
                        "subid": subscriber["subid"],
                        "subscription": subscriber["subscription"],
                        "affiliation": subscriber["affiliation"],
                    }
                )
                .returning(Model.PubsubSubscribers)
            )
            res = await con.execute(query)
            await con.commit()
            row = res.first()

            if row is not None:
                return Subscriber(**row._asdict())
            else:
                return None

    @staticmethod
    async def _update_pubsub_sub_database(item: Subscriber) -> Union[Subscriber, None]:
        async with await DB.connection_async() as con:
            query = (
                update(Model.PubsubSubscribers)
                .values(
                    {
                        "node": item["node"],
                        "jid": item["jid"],
                        "subscription": item["subscription"],
                        "affiliation": item["affiliation"],
                        "subid": item["subid"],
                    }
                )
                .returning(Model.PubsubSubscribers)
            )
            res = await con.execute(query)
            await con.commit()
            row = res.first()

            if row is not None:
                return Subscriber(**row._asdict())
            else:
                return None

    @staticmethod
    async def _delete_pubsub_sub_database(item: Subscriber) -> Union[Subscriber, None]:
        async with await DB.connection_async() as con:
            query = delete(Model.PubsubSubscribers).where(
                and_(
                    Model.PubsubSubscribers.c.node == item["node"],
                    Model.PubsubSubscribers.c.jid == JID(item["jid"]).bare(),
                    Model.PubsubSubscribers.c.subid == item["subid"],
                )
            )

            res = await con.execute(query)
            await con.commit()
            row = res.first()

            if row is not None:
                return Subscriber(**row._asdict())
            else:
                return None

    ###################################
    ############### ITEM ##############
    ###################################

    async def _insert_pubsub_item_memory(self, item: NodeItem) -> Union[NodeItem, None]:
        async with self._lock:
            if item["node"] in self._node_items:
                self._node_items.append(item)
                return item
            else:
                return None

    async def _update_pubsub_item_memory(self, item: NodeItem) -> Union[NodeItem, None]:
        async with self._lock:
            if item["node"] in self._node_items:
                match_index, match_node = next(
                    (
                        (i, n)
                        for i, n in enumerate(self._node_items[item["node"]])
                        if n["item_id"] == item["item_id"]
                    ),
                    None,
                )
                if match_node:
                    self._node_items[item["node"]][match_index] = item
                    return item

            return None

    async def _delete_pubsub_item_memory(
        self, node: str, itemid: str
    ) -> Union[NodeItem, None]:
        async with self._lock:
            match_index, match_node = next(
                (
                    (i, n)
                    for i, n in enumerate(self._node_items[node])
                    if n["item_id"] == itemid
                ),
                None,
            )
            if match_node:
                self._node_items[node].pop(match_index)
                return match_node

            return None

    @staticmethod
    async def _insert_pubsub_item_database(item: NodeItem) -> Union[NodeItem, None]:
        async with await DB.connection_async() as con:
            query = (
                insert(Model.PubsubItems)
                .values(
                    {
                        "node": item["node"],
                        "publisher": item["publisher"],
                        "item_id": item["item_id"],
                        "payload": item["payload"],
                    }
                )
                .returning(Model.PubsubItems)
            )
            res = await con.execute(query)
            await con.commit()
            row = res.first()

            if row is not None:
                return NodeItem(**row._asdict())
            else:
                return None

    @staticmethod
    async def _update_pubsub_item_database(item: NodeItem) -> Union[NodeItem, None]:
        async with await DB.connection_async() as con:
            query = (
                insert(Model.PubsubItems)
                .values(
                    {
                        "node": item["node"],
                        "publisher": item["publisher"],
                        "item_id": item["item_id"],
                        "payload": item["payload"],
                    }
                )
                .returning(Model.PubsubItems)
            )
            res = await con.execute(query)
            await con.commit()
            row = res.first()

            if row is not None:
                return NodeItem(**row._asdict())
            else:
                return None

    @staticmethod
    async def _delete_pubsub_item_database(item: NodeItem) -> Union[NodeItem, None]:
        async with await DB.connection_async() as con:
            query = (
                delete(Model.PubsubItems)
                .where(
                    and_(
                        Model.PubsubSubscribers.c.node == item["node"],
                        Model.PubsubSubscribers.c.item_id == item["item_id"],
                    )
                )
                .returning(Model.PubsubItems)
            )

            res = await con.execute(query)
            await con.commit()
            row = res.first()

            if row is not None:
                return NodeItem(**row._asdict())
            else:
                return None

    def _retrieve_operation(self, jid: JID, element: ET.Element):
        pubsub_element = element.find("{http://jabber.org/protocol/pubsub}pubsub")
        if pubsub_element is None:
            pubsub_element = element.find(
                "{http://jabber.org/protocol/pubsub}pubsub#owner"
            )
            if pubsub_element is None:
                return None

        operations: List[str] = []
        for child in pubsub_element:
            _, tag = CN.break_down(child.tag)
            operations.append(tag)

        if len(operations) > 1:
            return error_response(element, jid, ErrorType.MORE_THAT_ONE_OP)

        if len(operations) == 0:
            return error_response(element, jid, ErrorType.NOT_ACCEPTABLE)

        operation = operations.pop()
        operation_key = self._operations.get(operation, None)

        return getattr(self, operation_key or "", None)

    async def discover_items(self) -> List[Node]:
        """
        Returns the available nodes at the level specified in the query
        """
        async with self._lock:
            return self._nodes

    async def discover_info(self, node: str) -> Union[Node, None]:
        """
        Return the info for a given node
        """
        async with self._lock:
            return next((n for n in self._nodes if n["node"] == node), None)
