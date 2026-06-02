import asyncio
import xml.etree.ElementTree as ET
from typing import Union
from uuid import uuid4
from xml.etree.ElementTree import Element

import loguru

from pyjabber import AppConfig
from pyjabber.features.presence.Enums import PresenceShow, PresenceType
from pyjabber.features.presence.PresenceMixin import PresenceMixin
from pyjabber.features.presence.Wrappers import (
    ResourcePresence,
    PresenceInternalMessage,
    PIMType
)
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.queues.NewConnection import NewConnectionWrapper
from pyjabber.queues.QueueManager import QueueName, get_queue
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils.Singleton import singleton


@singleton
class Presence(PresenceMixin):
    _online_status: dict[str, dict[str, ResourcePresence]] = {}
    _pending: dict[JID, list[str]] = {}

    _lock = asyncio.Lock()
    _queue_task = None

    __slots__ = (
        "_handlers",
        "_connections",
        "_roster",
        "_connection_queue",
        "_internal_queue",
    )

    def __init__(self) -> None:
        self._handlers = {
            "subscribe": self._handle_subscribe,
            "subscribed": self._handle_subscribed,
            "unsubscribe": self._handle_unsubscribe,
            "unsubscribed": self._handle_unsubscribed,
            "unavailable": self._handle_global_presence,
            "INTERNAL": self._handle_lost_connection,
        }

        self._connections = ConnectionManager()
        self._connection_queue = get_queue(QueueName.CONNECTIONS)
        self._internal_queue = asyncio.Queue()

        self._roster = Roster()

    async def start(self):
        await self._load_pending_presence()
        async with self._lock:
            if self._queue_task:
                loguru.logger.warning(
                    "A queue handler task is already running for Presence."
                )
            else:
                self._queue_task = asyncio.create_task(self._internal_queue_handler())

    async def _internal_queue_handler(self):
        try:
            while True:
                res: PresenceInternalMessage = await self._internal_queue.get()
                if res["type"] == PIMType.CLIENT:
                    pass
                else:
                    pass
        except asyncio.CancelledError:
            pass

    async def put(self, value):
        await self._internal_queue.put(value)

    def put_nowait(self, value):
        self._internal_queue.put_nowait(value)

    async def update_pending_presence(self):
        pass

    async def feed(self, jid: JID, element: Element):
        if "to" not in element.attrib:
            return await self._handle_global_presence(jid, element)
        else:
            presence_type = element.attrib.get("type")
            if presence_type:
                return await self._handlers[presence_type](jid, element)
            else:
                return await self._handle_directed_presence(jid, element)

    async def _handle_subscribe(self, jid: JID, element: ET.Element):
        to_attrib = JID(element.attrib["to"]).bare()

        contact_id, contact_item = await self._roster.search_and_create_contact(
            jid, to_attrib
        )

        if contact_item.attrib.get("subscription") in ["to", "both"]:
            return ET.tostring(
                ET.Element(
                    "presence",
                    attrib={
                        "from": to_attrib,
                        "to": jid.bare(),
                        "id": element.attrib.get("id", str(uuid4())),
                        "type": "subscribed",
                    },
                )
            )

        if contact_item.attrib.get("ask") == "subscribe":
            return None
        else:
            new_item = contact_item.__copy__()
            new_item.attrib["ask"] = "subscribe"
            await self._roster.update_contact(jid, contact_id, new_item)

            petition = ET.tostring(
                ET.Element(
                    "presence",
                    attrib={
                        "from": jid.bare(),
                        "to": to_attrib,
                        "id": element.attrib.get("id", str(uuid4())),
                        "type": "subscribe",
                    },
                )
            )
            for client in await self._connections.get_transport(to_attrib):
                client.transport.write(petition)

            return None

    async def _handle_subscribed(self, jid: JID, element: ET.Element):
        to_attrib = JID(element.attrib["to"]).bare()

        roster_push_sender: Union[None, ET.Element] = None
        roster_push_receiver: Union[None, ET.Element] = None

        roster_receiver = await self._roster.search_contact(JID(to_attrib), jid.bare())
        if not roster_receiver:
            return ET.tostring(
                ET.Element(
                    "presence",
                    attrib={
                        "from": to_attrib,
                        "to": jid.bare(),
                        "id": element.attrib.get("id", str(uuid4())),
                        "type": "unsubscribe",
                    },
                )
            )

        contact_id, contact_item = roster_receiver
        if contact_item.attrib.get("subscription") in ["none", "from"]:
            ask_attrib = contact_item.attrib.get("ask")
            if ask_attrib is None:
                return ET.tostring(
                    ET.Element(
                        "presence",
                        attrib={
                            "from": to_attrib,
                            "to": jid.bare(),
                            "id": element.attrib.get("id", str(uuid4())),
                            "type": "unsubscribe",
                        },
                    )
                )

            new_item = contact_item.__copy__()
            new_item.attrib.pop("ask")

            if contact_item.attrib.get("subscription") == "none":
                new_item.attrib["subscription"] = "to"
            else:
                new_item.attrib["subscription"] = "both"

            await self._roster.update_contact(
                JID(to_attrib), contact_id, ET.tostring(new_item)
            )
            roster_push_receiver = new_item

        roster_sender = await self._roster.search_and_create_contact(
            JID(jid.bare()), to_attrib
        )

        contact_id, contact_item = roster_sender
        if contact_item.attrib.get("subscription") in ["none", "to"]:
            new_item = contact_item.__copy__()
            if contact_item.attrib.get("subscription") == "none":
                new_item.attrib["subscription"] = "from"
            else:
                new_item.attrib["subscription"] = "both"

            await self._roster.update_contact(JID(jid.bare()), contact_id, new_item)
            roster_push_sender = new_item

        if roster_push_receiver:
            for receiver in await self._connections.get_transport(JID(to_attrib)):
                res = IQ(to=str(receiver.jid), type_=IQ.TYPE.SET)
                query = ET.SubElement(res, "{jabber:iq:roster}query")
                query.append(roster_push_receiver)
                receiver.transport.write(ET.tostring(res))

        if roster_push_sender:
            for sender in await self._connections.get_transport(JID(jid.bare())):
                res = IQ(to=str(sender.jid), type_=IQ.TYPE.SET)
                query = ET.SubElement(res, "{jabber:iq:roster}query")
                query.append(roster_push_sender)
                sender.transport.write(ET.tostring(res))

        return None

    async def _handle_unsubscribe(self, jid: JID, element: ET.Element):
        to_attrib = JID(element.attrib["to"]).bare()

        roster_push_sender: Union[None, ET.Element] = None
        roster_push_receiver: Union[None, ET.Element] = None

        roster_receiver = await self._roster.search_contact(JID(to_attrib), jid.bare())
        if not roster_receiver:
            return ET.tostring(
                ET.Element(
                    "presence",
                    attrib={
                        "from": to_attrib,
                        "to": jid.bare(),
                        "id": element.attrib.get("id", str(uuid4())),
                        "type": "unsubscribed",
                    },
                )
            )

        contact_id, contact_item = roster_receiver
        if contact_item.attrib.get("subscription") in ["both", "from"]:
            new_item = contact_item.__copy__()
            new_item.attrib.pop("ask", None)

            if contact_item.attrib.get("subscription") == "both":
                new_item.attrib["subscription"] = "to"
            else:
                new_item.attrib["subscription"] = "none"

            await self._roster.update_contact(
                JID(to_attrib), contact_id, ET.tostring(new_item)
            )
            roster_push_receiver = new_item

        roster_sender = await self._roster.search_and_create_contact(
            JID(jid.bare()), to_attrib
        )

        contact_id, contact_item = roster_sender
        if contact_item.attrib.get("subscription") in ["both", "to"]:
            new_item = contact_item.__copy__()

            if contact_item.attrib.get("subscription") == "both":
                new_item.attrib["subscription"] = "from"
            else:
                new_item.attrib["subscription"] = "none"

            await self._roster.update_contact(JID(jid.bare()), contact_id, new_item)
            roster_push_sender = new_item

        if roster_push_receiver:
            for receiver in self._connections.get_transport(JID(to_attrib)):
                res = IQ(to=str(receiver.jid), type_=IQ.TYPE.SET)
                query = ET.SubElement(res, "{jabber:iq:roster}query")
                query.append(roster_push_receiver)
                receiver.transport.write(ET.tostring(res))

        if roster_push_sender:
            for sender in self._connections.get_transport(JID(jid.bare())):
                res = IQ(to=str(sender.jid), type_=IQ.TYPE.SET)
                query = ET.SubElement(res, "{jabber:iq:roster}query")
                query.append(roster_push_sender)
                sender.transport.write(ET.tostring(res))

        return None

    async def _handle_unsubscribed(self, jid: JID, element: ET.Element):
        to_attrib = JID(element.attrib["to"]).bare()

        roster_push_sender: Union[None, ET.Element] = None
        roster_push_receiver: Union[None, ET.Element] = None

        roster_receiver = await self._roster.search_contact(JID(to_attrib), jid.bare())
        if roster_receiver:
            contact_id, contact_item = roster_receiver
            if contact_item.attrib.get("subscription") in ["to", "both"]:
                new_item = contact_item.__copy__()
                new_item.attrib.pop("ask", None)

                if contact_item.attrib.get("subscription") == "both":
                    new_item.attrib["subscription"] = "from"
                else:
                    new_item.attrib["subscription"] = "none"

                await self._roster.update_contact(
                    JID(to_attrib), contact_id, ET.tostring(new_item)
                )
                roster_push_receiver = new_item

        roster_sender = await self._roster.search_and_create_contact(
            JID(jid.bare()), to_attrib
        )

        contact_id, contact_item = roster_sender
        if contact_item.attrib.get("subscription") in ["from", "both"]:
            new_item = contact_item.__copy__()
            if contact_item.attrib.get("subscription") == "both":
                new_item.attrib["subscription"] = "to"
            else:
                new_item.attrib["subscription"] = "none"

            await self._roster.update_contact(
                JID(jid.bare()), contact_id, ET.tostring(new_item)
            )
            roster_push_sender = new_item

        if roster_push_receiver:
            for receiver in await self._connections.get_transport(JID(to_attrib)):
                res = IQ(to=str(receiver.jid), type_=IQ.TYPE.SET)
                query = ET.SubElement(res, "{jabber:iq:roster}query")
                query.append(roster_push_receiver)
                receiver.transport.write(ET.tostring(res))

        if roster_push_sender:
            for sender in await self._connections.get_transport(JID(jid.bare())):
                res = IQ(to=str(sender.jid), type_=IQ.TYPE.SET)
                query = ET.SubElement(res, "{jabber:iq:roster}query")
                query.append(roster_push_sender)
                sender.transport.write(ET.tostring(res))

        return None

    async def _handle_global_presence(self, jid: JID, element: ET.Element):
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
        try:
            priority = next(
                (
                    int(c.text or 0)
                    for c in element
                    if c.tag == "{jabber:client}priority"
                ),
                0,
            )
        except (TypeError, ValueError):
            priority = 0

        resource_presence_old = await self._get_present_online(jid)
        type_presence = element.attrib.get("type")

        if type_presence is None or type_presence == PresenceType.AVAILABLE.value:
            if resource_presence_old:
                presence_type = resource_presence_old.get("presence_type", None)
                if presence_type:
                    if presence_type == PresenceType.UNAVAILABLE.value:
                        await self._connection_queue.put(NewConnectionWrapper(jid))
                        await self._connections.online(jid)

            await self._update_present_online(
                jid,
                {
                    "presence_type": PresenceType.AVAILABLE,
                    "show": show,
                    "status": status,
                    "priority": priority,
                },
            )

            await self._connections.online(jid)

        elif type_presence == PresenceType.UNAVAILABLE.value:
            await self._update_present_online(
                jid,
                {
                    "presence_type": PresenceType.UNAVAILABLE,
                    "show": show,
                    "status": status,
                    "priority": priority,
                },
            )
            await self._connections.offline(jid)

        else:
            loguru.logger.error(
                "Malformed presence type. Not in <available | unavailable>"
            )
            raise Exception

        for contact_item in await self._roster.roster_by_jid(jid):
            contact = ET.fromstring(contact_item)
            if contact.attrib.get("subscription") not in ["from", "both"]:
                continue

            contact_jid = JID(contact.attrib.get("jid"))
            if contact_jid.domain in AppConfig.app_config.domains:
                if contact_jid.bare() not in self._online_status:
                    continue

                resources_online = await self._get_present_online_list(contact_jid)
                if resources_online is None or not resources_online:
                    loguru.logger.error(
                        f"<{str(jid)}> present in online list, "
                        f"but has not any resource connected."
                    )
                    continue

                for resource, presence in resources_online.items():
                    if presence["presence_type"] == PresenceType.AVAILABLE.value:
                        contact_client = await self._connections.get_transport(
                            JID(
                                user=contact_jid.user,
                                domain=contact_jid.domain,
                                resource=resource,
                            )
                        )
                        if not contact_client:
                            loguru.logger.error(
                                f"<{contact_jid}{resource}> is in the online list "
                                f"but cannot retrieve transport"
                            )
                            continue

                        presence = ET.Element(
                            "presence",
                            attrib={
                                "from": str(jid),
                                "to": f"{contact_jid}{resource}",
                                "type": presence["presence_type"].value,
                            },
                        )
                        if "show" in presence:
                            show_et = ET.SubElement(presence, "show")
                            show_et.text = presence["show"]
                        if "status" in presence:
                            status_et = ET.SubElement(presence, "status")
                            status_et.text = presence["status"]
                        if "priority" in presence:
                            priority_et = ET.SubElement(presence, "priority")
                            priority_et.text = presence["priority"]

                        contact_client.transport.write(ET.tostring(presence))
            else:
                pass #TODO: Reroute presence to external server (S2S)

        await self._initial_presence_broadcast(jid)

    async def _handle_lost_connection_server(self, host: str, element: Element):
        pass

    async def _handle_lost_connection(self, jid: JID, element: Element):
        resource_presence = await self._remove_present_online(jid)
        if resource_presence:
            for contact in await self._roster.roster_by_jid(jid):
                item = ET.fromstring(contact.get("item"))
                if item.attrib.get("subscription") not in ["from", "both"]:
                    continue

                contact_jid = JID(item.attrib.get("jid"))
                if contact_jid.domain not in AppConfig.app_config.domains:
                    pass # TODO: manage remote server foreword

                resources_online_list = await self._connections.get_transport_online(
                    JID(contact_jid.bare())
                )
                for client in resources_online_list:
                    jid, transport, _ = client
                    presence = ET.Element(
                        "presence",
                        attrib={
                            "from": str(jid),
                            "to": str(jid) ,
                            "type": PresenceType.UNAVAILABLE.value,
                        },
                    )
                    transport.write(ET.tostring(presence))


    async def _handle_directed_presence(self, jid: JID, element: ET.Element):
        to = JID(element.attrib.get("to"))
        if str(jid) != element.attrib.get("from", None):
            element.attrib["from"] = str(jid)

        if to.domain in AppConfig.app_config.domains:
            for client in await self._connections.get_transport_online(JID(to.bare())):
                client.transport.write(ET.tostring(element))
        else:
            pass # TODO: manage remote server foreword

    async def _handle_unavailable(self, jid: JID, element: ET.Element):
        roster = await self._roster.roster_by_jid(jid)
        for item in roster:
            to = ET.fromstring(item).attrib.get("jid", None)
            if not to:
                continue

            to = JID(to)
            if to.domain in AppConfig.app_config.domains:
                for client in await self._connections.get_transport_online(
                    JID(to.bare())
                ):
                    presence = ET.tostring(
                        ET.Element(
                            "presence",
                            attrib={
                                "from": str(jid),
                                "to": str(client.jid),
                                "type": PresenceType.UNAVAILABLE.value
                            },
                        )
                    )
                    client.transport.write(presence)
            else:
                pass # TODO: manage remote server foreword

