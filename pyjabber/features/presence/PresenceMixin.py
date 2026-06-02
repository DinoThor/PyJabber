from typing import TYPE_CHECKING, List, Tuple, Union

from sqlalchemy import delete, select, insert

from pyjabber.AppConfig import AppConfig
from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.features.presence.Enums import (
    PresenceType,
    PresenceShow,
    PresenceShowWeights,
)
from pyjabber.features.presence.Wrappers import JIDPresence, ResourcePresence
from pyjabber.network.ConnectionManager import Client
from pyjabber.stream.JID import JID

import xml.etree.ElementTree as ET

if TYPE_CHECKING:
    from pyjabber.features.presence.PresenceFeature import Presence
    BaseClass = Presence
else:
    BaseClass = object

class PresenceMixin(BaseClass):
    async def _load_pending_presence(self):
        """
        Loads the pending presence subscriptions from database
        into memory.
        Used only in the first instance of Presence class.
        """
        async with await DB.connection_async() as con:
            query = select(Model.PendingSubs.c.jid, Model.PendingSubs.c.item)
            res = await con.execute(query)
            res = res.fetchall()
        async with self._lock:
            for jid, item in res:
                jid = JID(jid)
                if jid not in self._pending:
                    self._pending[jid] = [item]
                else:
                    self._pending[jid].append(item)

    @staticmethod
    async def _insert_pending_presence(jid: JID, raw_item: str):
        async with await DB.connection_async() as con:
            query = insert(Model.PendingSubs).values(
                {"jid": jid.bare(), "item": raw_item}
            )
            await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

    async def _delete_pending_presence(self, jid: JID):
        """
        Deletes the pending presence from both database and memory.
        It will delete all the elements store.
        It is use is intended when a previous function has treated all
        pending items.
        """
        async with await DB.connection_async() as con:
            query = delete(Model.PendingSubs).where(Model.PendingSubs.c.jid == jid.bare())
            await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()
        async with self._lock:
            self._pending[jid].pop()

    def _most_priority(self, jid: JID) -> Union[None, Tuple[str, ResourcePresence]]:
        """
        Returns the resource with the max value in priority.
        In case of draw, it will select via its show status.
        """
        resources_presence: dict[str, ResourcePresence] = self._online_status.get(
            jid.bare(), None
        )
        if resources_presence is None:
            return None

        key_max, sub_dict_max = max(
            resources_presence.items(),
            key=lambda item: (
                item[1]["priority"],                # Priority
                PresenceShowWeights[item[1]["show"] # Show
                if item[1]["show"] is not None else PresenceShow.NONE],
            ),
        )

        return key_max, sub_dict_max

    async def _get_present_online(self, jid: JID) -> Union[None, ResourcePresence]:
        """
        Returns the presence status for a given jid
        The JID MUST contain a resource.
        """
        if jid.resource is None:
            raise ValueError("<resource> attribute is None in jid parameter")

        async with self._lock:
            if (
                jid.bare() in self._online_status
                and jid.resource in self._online_status[jid.bare()]
            ):
                return self._online_status[jid.bare()][jid.resource]

        return None

    async def _get_present_online_list(self, jid: JID) -> dict[str, ResourcePresence]:
        """
        Returns the presence status list of resources for a given jid.
        """
        async with self._lock:
            return self._online_status.get(jid.bare(), {})

    async def _remove_present_online(self, jid: JID) -> Union[None, ResourcePresence]:
        """
        Remove the presence status for a given jid
        The JID MUST contain a resource.
        """
        if jid.resource is None:
            raise ValueError("<resource> attribute is None in jid parameter")

        async with self._lock:
            if jid.bare() in self._online_status:
                presence = self._online_status[jid.bare()].pop(jid.resource, None)
                return presence
            else:
                return None

    async def _get_pending_list(self, jid: JID) -> list[str]:
        """
        Returns the pending list of resources for a given jid.
        It can be with or without ``resource``
        """
        async with self._lock:
            return self._pending.get(jid.bare(), [])

    async def _update_present_online(
        self, jid: JID, new_presence: ResourcePresence
    ) -> None:
        """
        Updates the presence status for a given jid
        The JID MUST contain a resource.
        """
        if jid.resource is None:
            raise ValueError("<resource> attribute is None in jid parameter")

        async with self._lock:
            if jid.bare() in self._online_status:
                self._online_status[jid.bare()][jid.resource] = new_presence
            else:
                self._online_status[jid.bare()] = {}
                self._online_status[jid.bare()][jid.resource] = new_presence

    async def _update_presence_online_list(self, jid: JID) -> Union[None, JIDPresence]:
        pass

    async def _initial_presence_broadcast(self, jid: JID) -> None:
        pending_items = await self._get_pending_list(jid)
        for raw_item in pending_items:
            client: Client = self._connections.get_transport(jid)
            client.transport.write(raw_item)

        roster = await self._roster.roster_by_jid(jid)
        for raw_contact in roster:
            contact = ET.fromstring(raw_contact)
            contact_jid = contact.attrib.get("jid", None)
            if contact_jid is None:
                continue

            contact_jid = JID(contact_jid)
            resources_presence = await self._get_present_online_list(contact_jid)
            for resource, presence in resources_presence.items():
                resource_client = self._connections.get_transport(JID(
                    user=contact_jid.user,
                    domain=contact_jid.domain,
                    resource=resource,
                ))
                if resource_client:
                    presence_res = ET.Element(
                        "presence",
                        attrib={"type": presence["presence_type"].value}
                    )
                    if "show" in presence:
                        show = ET.SubElement(presence_res, "show")
                        show.text = presence["show"]
                    if "status" in presence:
                        status = ET.SubElement(presence_res, "status")
                        status.text = presence["status"]
                    if "priority" in presence:
                        priority = ET.SubElement(presence_res, "priority")
                        priority.text = str(presence["priority"])
                    resource_client.transport.write(presence)


