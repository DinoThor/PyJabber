import asyncio
import xml.etree.ElementTree as ET
from typing import List, Tuple, Union
from uuid import uuid4
from xml.etree.ElementTree import Element

from sqlalchemy import delete, select

from pyjabber import AppConfig
from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.features.presence.Enums import PresenceShow, PresenceType
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.queues.NewConnection import NewConnectionWrapper
from pyjabber.queues.QueueManager import QueueName, get_queue
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton


class Presence(metaclass=Singleton):
    __slots__ = (
        "_handlers",
        "_connections",
        "_roster",
        "_pending",
        "_connection_queue",
        "_internal_queue",
        "_online_status",
    )

    def __init__(self) -> None:
        self._handlers = {
            "subscribe": self._handle_subscribe,
            "subscribed": self._handle_subscribed,
            "unsubscribed": self._handle_unsubscribed,
            "unavailable": self._handle_global_presence,
            "INTERNAL": self._handle_lost_connection,
        }

        self._connections = ConnectionManager()
        self._connection_queue = get_queue(QueueName.CONNECTIONS)
        self._internal_queue = asyncio.Queue()

        self._roster = Roster()
        self._pending = {}

        self._online_status = {}

    async def get_all_pending_presence(self):
        async with await DB.connection_async() as con:
            query = select(Model.PendingSubs.c.jid, Model.PendingSubs.c.item)
            res = await con.execute(query)
            res = res.fetchall()

        for jid_from, jid_to, item in res:
            if jid_to not in self._pending:
                self._pending[jid_to] = [item]
            else:
                self._pending[jid_to].append(item)

    async def update_pending_presence(self):
        pass

    async def delete_pending_presence(self, jid: str):
        async with await DB.connection_async() as con:
            query = delete(Model.PendingSubs).where(Model.PendingSubs.c.jid == jid)
            await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

        self._pending[jid].pop()

    def priority_by_jid(self, jid: JID):
        try:
            return self._online_status[jid.bare()]
        except KeyError:
            return []

    def most_priority(
        self, jid: JID
    ) -> List[
        Tuple[str, PresenceType, Union[str, None], Union[str, None], Union[str, None]]
    ]:
        priority = self.priority_by_jid(jid)

        values = [item[-1] for item in priority if item[-1] is not None]
        max_value = max(values) if values else None
        return [item for item in priority if item[-1] == max_value]

    async def put(self, value):
        await self._internal_queue.put(value)

    def put_nowait(self, value):
        self._internal_queue.put_nowait(value)

    async def feed(self, jid: JID, element: Element):
        if "to" not in element.attrib:
            return await self._handle_global_presence(jid, element)
        else:
            if "type" in element.attrib:
                return await self._handlers[element.get("type")](jid, element)
            else:
                return await self._handle_directed_presence(jid, element)

    async def _present_in_online_list(self, jid: JID):
        if jid.bare() not in self._online_status:
            return None, None

        present = [
            (i, p)
            for i, p in enumerate(self._online_status[jid.bare()])
            if p[0] == jid.resource
        ]
        if present:
            return present[0]
        return None, None

    def _handle_lost_connection(self, jid: Union[JID, str], element: Element):
        if isinstance(jid, JID):
            if jid.bare() not in self._online_status:
                return None

            index, present = self._present_in_online_list(jid)
            if present:
                if (
                    self._online_status[jid.bare()][index][1]
                    == PresenceType.UNAVAILABLE
                ):
                    self._online_status[jid.bare()].pop(index)
                    if len(self._online_status[jid.bare()]) == 0:
                        self._online_status.pop(jid.bare())
                    return None

            for contact in self._roster.roster_by_jid(jid):
                item = ET.fromstring(contact.get("item"))
                if item.attrib.get("subscription") not in ["from", "both"]:
                    continue

                contact_jid = item.attrib.get("jid")

                if len(contact_jid.split("@")) < 2:
                    contact_jid = JID(contact_jid + f"@{AppConfig.app_config.host}")
                else:
                    contact_jid = JID(contact_jid)

                if contact_jid.bare() in self._online_status:
                    for user_connected in [
                        i
                        for i in self._online_status[contact_jid.bare()]
                        if i[1] == PresenceType.AVAILABLE
                    ]:
                        resource = user_connected[0]
                        client = self._connections.get_transport(
                            JID(
                                user=contact_jid.user,
                                domain=contact_jid.domain,
                                resource=resource,
                            )
                        )[0]

                        presence = ET.Element(
                            "presence",
                            attrib={
                                "from": str(jid),
                                "to": client.jid.bare(),
                                "type": PresenceType.UNAVAILABLE.value,
                            },
                        )
                        client.transport.write(ET.tostring(presence))

            for client in self._connections.get_transport(JID(jid.bare())):
                presence = ET.Element(
                    "presence",
                    attrib={
                        "from": str(jid),
                        "to": jid.bare(),
                        "type": PresenceType.UNAVAILABLE.value,
                    },
                )
                client.transport.write(ET.tostring(presence))
        else:
            pass  # TODO: presence for remote server lost

    async def _handle_lost_connection_server(self, host: str, element: Element):
        pass

    async def _handle_global_presence(self, jid: JID, element: ET.Element):
        if jid.bare() not in self._online_status:
            self._online_status[jid.bare()] = []

        show = next(
            (
                c.text
                for c in element
                if c.tag == "{jabber:client}show"
                and c.text in [i.value for i in PresenceShow]
            ),
            None,
        )
        status = next(
            (c.text for c in element if c.tag == "{jabber:client}status"), None
        )
        priority = next(
            (c.text for c in element if c.tag == "{jabber:client}priority"), None
        )

        index, present = await self._present_in_online_list(jid)
        if element.attrib.get("type") == PresenceType.UNAVAILABLE.value:
            if present:
                self._online_status[jid.bare()][index] = (
                    jid.resource,
                    PresenceType.UNAVAILABLE,
                    show,
                    status,
                    priority,
                )
            else:
                self._online_status[jid.bare()].append(
                    (jid.resource, PresenceType.UNAVAILABLE, show, status, priority)
                )

            self._connections.online(jid, False)
        else:
            if present:
                previous_status = self._online_status[jid.bare()][index][1]
                self._online_status[jid.bare()][index] = (
                    jid.resource,
                    PresenceType.AVAILABLE,
                    show,
                    status,
                    priority,
                )
                if previous_status == PresenceType.UNAVAILABLE:
                    await self._connection_queue.put(
                        NewConnectionWrapper(jid)
                        # ('CONNECTION', jid)
                    )
            else:
                self._online_status[jid.bare()].append(
                    (jid.resource, PresenceType.AVAILABLE, show, status, priority)
                )
                await self._connection_queue.put(
                    NewConnectionWrapper(jid)
                    # ('CONNECTION', jid)
                )

            self._connections.online(jid)

        for contact in self._roster.roster_by_jid(jid):
            item = ET.fromstring(contact.get("item"))
            if item.attrib.get("subscription") not in ["from", "both"]:
                continue

            contact_jid = item.attrib.get("jid")

            if len(contact_jid.split("@")) < 2:
                contact_jid = JID(contact_jid + f"@{AppConfig.app_config.host}")
            else:
                contact_jid = JID(contact_jid)

            if contact_jid.bare() in self._online_status:
                for user_connected in [
                    i
                    for i in self._online_status[contact_jid.bare()]
                    if i[1] == PresenceType.AVAILABLE
                ]:
                    resource = user_connected[0]
                    online = self._connections.get_transport_online(
                        JID(
                            user=contact_jid.user,
                            domain=contact_jid.domain,
                            resource=resource,
                        )
                    )
                    if online:
                        online = online.pop()
                        presence = ET.Element(
                            "presence",
                            attrib={
                                "from": str(jid),
                                "to": online.jid.bare(),
                            },
                        )

                        if element.attrib.get("type") == PresenceType.UNAVAILABLE.value:
                            presence.attrib["type"] = PresenceType.UNAVAILABLE.value

                        if show:
                            show_et = ET.SubElement(presence, "show")
                            show_et.text = show

                        if status:
                            status_et = ET.SubElement(presence, "status")
                            status_et.text = status

                        if priority:
                            priority_et = ET.SubElement(presence, "priority")
                            priority_et.text = priority

                        online.transport.write(ET.tostring(presence))

        if jid.bare() in self._pending:
            for item in self._pending[jid.bare()]:
                for client in self._connections.get_transport(jid):
                    client.transport.write(item)
            await self.delete_pending_presence(jid.bare())

        return None

    async def _handle_directed_presence(self, jid: JID, element: ET.Element):
        to = JID(element.attrib.get("to"))
        element.attrib["from"] = str(jid)

        if to.domain == AppConfig.app_config.host:
            for client in self._connections.get_transport(jid):
                client.transport.write(ET.tostring(element))

    async def _handle_subscribe(self, jid: JID, element: ET.Element):
        to = JID(element.attrib.get("to"))

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        # Handle local presence. Receiver client connected to the protocols
        if to.domain == AppConfig.app_config.host:
            roster = self._roster.roster_by_jid(jid)

            item = [
                item
                for item in roster
                if ET.fromstring(item.get("item")).attrib.get("jid") == to.user
                or ET.fromstring(item.get("item")).attrib.get("jid") == to.bare()
            ]

            if not item:
                await self._roster.create_roster_entry(jid, to)
                roster = self._roster.roster_by_jid(jid)
                item = [
                    item
                    for item in roster
                    if ET.fromstring(item.get("item")).attrib["jid"] == to.user
                    or ET.fromstring(item.get("item")).attrib["jid"] == to.bare()
                ]

            roster_item = item[0].get("item")
            et_item = ET.fromstring(roster_item)
            item_id = item[0].get("id")

            if et_item.attrib.get("ask") == "subscribe":
                return

            if et_item.attrib.get("subscription") in ["to", "both"]:
                petition = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib.get("to"),
                        "to": element.attrib.get("from"),
                        "id": element.attrib.get("id") or str(uuid4()),
                        "type": "subscribed",
                    },
                )
                return ET.tostring(petition)

            if "ask" not in et_item.attrib:
                new_item = et_item.__copy__()
                new_item.attrib["ask"] = "subscribe"
                await self._roster.update_item(new_item, item_id)

            for client in self._connections.get_transport(to):
                petition = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib.get("from"),
                        "to": element.attrib.get("to"),
                        "id": element.attrib.get("id") or str(uuid4()),
                        "type": "subscribe",
                    },
                )
                client.transport.write(ET.tostring(petition))

            else:
                await self._roster.store_pending_sub(to.bare(), element)

    async def _handle_subscribed(self, jid: JID, element: ET.Element):
        to = JID(element.attrib.get("to"))

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        # Handle local presence. Receiver client connected to the protocols
        if to.domain == AppConfig.app_config.host:
            roster_sender = self._roster.roster_by_jid(to)
            roster_receiver = self._roster.roster_by_jid(jid)

            if not roster_sender:
                return None

            if not roster_receiver:
                await self._roster.create_roster_entry(JID(jid.bare()), to)
                roster_receiver = self._roster.roster_by_jid(jid)

            roster_push_sender = None
            roster_push_receiver = None

            item_sender = [  # Sender appears in receiver roster
                item
                for item in roster_sender
                if ET.fromstring(item.get("item")).attrib.get("jid") == jid.user
            ]

            item_receiver = [  # Receiver appears in sender roster
                item
                for item in roster_receiver
                if ET.fromstring(item.get("item")).attrib.get("jid") == to.user
            ]

            if item_sender:
                item_id = item_sender[0].get("id")
                item_sender = item_sender[0].get("item")
                et_item_sender = ET.fromstring(item_sender)

                if et_item_sender.attrib.get("subscription") == "none":
                    new_item_sender = et_item_sender.__copy__()
                    if "ask" in new_item_sender.attrib:
                        new_item_sender.attrib.pop("ask")

                    new_item_sender.attrib["subscription"] = "to"
                    await self._roster.update_item(new_item_sender, item_id)

                    new_item_sender.attrib["jid"] = (
                        new_item_sender.attrib["jid"] + f"@{AppConfig.app_config.host}"
                    )
                    roster_push_sender = new_item_sender

                elif et_item_sender.attrib.get("subscription") == "from":
                    new_item_sender = et_item_sender.__copy__()
                    if "ask" in new_item_sender.attrib:
                        new_item_sender.attrib.pop("ask")

                    new_item_sender.attrib["subscription"] = "both"
                    await self._roster.update_item(new_item_sender, item_id)

                    new_item_sender.attrib["jid"] = (
                        new_item_sender.attrib["jid"] + f"@{AppConfig.app_config.host}"
                    )
                    roster_push_sender = new_item_sender

                else:
                    item_sender = None

            if item_receiver:
                item_id = item_receiver[0].get("id")
                item_receiver = item_receiver[0].get("item")
                et_item_receiver = ET.fromstring(item_receiver)

                if et_item_receiver.attrib.get("subscription") == "none":
                    new_item_receiver = et_item_receiver.__copy__()
                    new_item_receiver.attrib["subscription"] = "from"
                    await self._roster.update_item(new_item_receiver, item_id)

                    new_item_receiver.attrib["jid"] = (
                        new_item_receiver.attrib["jid"]
                        + f"@{AppConfig.app_config.host}"
                    )
                    roster_push_receiver = new_item_receiver

                elif et_item_receiver.attrib["subscription"] == "to":
                    new_item_receiver = et_item_receiver.__copy__()
                    new_item_receiver.attrib["subscription"] = "both"
                    await self._roster.update_item(new_item_receiver, item_id)

                    new_item_receiver.attrib["jid"] = (
                        new_item_receiver.attrib["jid"]
                        + f"@{AppConfig.app_config.host}"
                    )
                    roster_push_receiver = new_item_receiver

                else:
                    item_receiver = None

            if item_receiver:
                for sender in self._connections.get_transport(JID(to.bare())):
                    res = ET.Element(
                        "presence",
                        attrib={
                            "from": jid.bare(),
                            "to": str(to),
                            "id": element.attrib.get("id") or str(uuid4()),
                            "type": "subscribed",
                        },
                    )
                    sender.transport.write(ET.tostring(res))
                return None

            if roster_push_sender is not None:
                for sender in self._connections.get_transport(JID(to.bare())):
                    res = IQ(to=str(sender.jid), type_=IQ.TYPE.SET)
                    query = ET.SubElement(
                        res, "query", attrib={"xmlns": "jabber:iq:roster"}
                    )
                    query.append(roster_push_sender)

                    sender.transport.write(ET.tostring(res))

            if roster_push_receiver is not None:
                for receiver in self._connections.get_transport(JID(jid.bare())):
                    res = IQ(to=str(receiver.jid), type_=IQ.TYPE.SET)
                    query = ET.SubElement(
                        res, "query", attrib={"xmlns": "jabber:iq:roster"}
                    )
                    query.append(roster_push_receiver)

                    receiver.transport.write(ET.tostring(res))

    async def _handle_unsubscribed(self, jid: JID, element: ET.Element):
        to = JID(element.attrib["to"])

        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        # Handle locally
        if to.domain == AppConfig.app_config.host:
            roster = self._roster.roster_by_jid(jid)
            item = [
                item
                for item in roster
                if ET.fromstring(item.get("item")).attrib.get("jid")
                in [to.bare(), to.user]
            ]

            if not item:
                return

            item_id = item[0].get("id")
            item = item[0].get("item")
            et_item = ET.fromstring(item)
            new_item = et_item.__copy__()

            updated = False

            if et_item.attrib.get("subscription") == "to":
                new_item.attrib["subscription"] = "none"
                await self._roster.update_item(item=new_item, id_=item_id)
                updated = True

            elif et_item.attrib.get("subscription") == "both":
                new_item.attrib["subscription"] = "from"
                await self._roster.update_item(item=new_item, id_=item_id)
                updated = True

            elif "ask" in et_item.attrib:
                new_item.attrib.pop("ask")
                await self._roster.update_item(item=new_item, id_=item_id)

            if updated:
                presence = ET.Element(
                    "presence",
                    attrib={
                        "from": element.attrib.get("from"),
                        "to": to.bare(),
                        "id": str(uuid4()),
                        "type": "unsubscribed",
                    },
                )
                for buffer in self._connections.get_transport(to):
                    buffer.transport.write(ET.tostring(presence))

    async def _handle_unavailable(self, jid: JID, element: ET.Element):
        if "from" not in element.attrib:
            element.attrib["from"] = str(jid)

        roster = self._roster.roster_by_jid(jid)
        for item in roster:
            to = ET.fromstring(item[-1]).attrib.get("jid")

            if to.split("@")[1] == AppConfig.app_config.host:
                presence = element.__copy__()
                presence.attrib["to"] = to

                for client in self._connections.get_transport(JID(to)):
                    client.transport.write(ET.tostring(presence))
