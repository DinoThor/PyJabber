import asyncio
import xml.etree.ElementTree as ET

from sqlalchemy import and_, delete, insert, select, update

from pyjabber import AppConfig
from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID


class Roster:
    """
    Roster plugin.

    Manages the roster list for each registered user in the protocols.

    A roster in XMPP is a protocols-stored contact list that manages contacts,
    presence status, and subscription requests.
    It enables real-time presence updates, contact organization, and
    synchronization across devices, ensuring seamless and private communication.
    """
    _roster_in_memory = {}
    _lock = asyncio.Lock()

    __slots__ = ("_handlers",)

    def __init__(self) -> None:
        self._handlers = {
            "get": self.handle_get,
            "set": self.handle_set,
            "result": self.handle_result,
        }

    async def start(self):
        """
        Initialize the roster plugin.
        MUST BE CALLED right after its instantiation.
        """
        await self._load_roster_in_memory()

    async def feed(self, jid: JID, element: ET.Element):
        """
        Entry point of the plugin
        """
        if len(element) != 1:
            return SE.invalid_xml()

        iq_type = element.attrib.get("type")
        if iq_type not in ["get", "set", "result"]:
            return SE.invalid_xml()

        return await self._handlers[iq_type](jid, element)

    async def handle_get(self, jid: JID, element: ET.Element):
        """
        Search in the roster of the given jid and
        returns all the registered contacts
        """
        jid = str(jid) if jid.domain == AppConfig.app_config.host else jid.bare()
        roster = self._roster_in_memory.get(jid, [])

        iq = IQ(type_=IQ.TYPE.RESULT, id_=element.attrib.get("id"))
        query = ET.SubElement(iq, "{jabber:iq:roster}query")

        for item in roster:
            query.append(ET.fromstring(item.get("item")))

        return ET.tostring(iq)

    async def handle_set(self, jid: JID, element: ET.Element):
        query = element.find("{jabber:iq:roster}query")
        if query is None:
            return SE.invalid_xml()

        jid = jid.user if jid.domain == AppConfig.app_config.host else jid.bare()
        new_item = query.findall("{jabber:iq:roster}item")

        if len(new_item) != 1:
            return SE.invalid_xml()

        new_item = new_item[0]

        roster = self._roster_in_memory.get(jid, None)
        if roster:
            match_entry = next((
                k for k, v in roster.items()
                if v.get("roster_item").get("jid") == new_item.attrib.get("jid")
            ), None)

            if match_entry:
                id_roster = roster[match_entry].get("id")
                if new_item.attrib.get("subscription") == "remove":
                    await self._delete_item_from_database(jid, id_roster)
                    await self._roster_memory_delete(jid, id_roster)
                else:
                    updated_item = await self._update_item_from_database(
                        jid, id_roster, new_item
                    )
                    await self._roster_memory_update(jid, id_roster, updated_item)
            else:
                await self._create_item_into_database(jid, new_item)
        else:
            created_id, created_item = await self._create_item_into_database(
                jid, new_item
            )
            await self._roster_memory_insert(jid, created_id, created_item)

        res = IQ(id_=element.attrib.get("id"), type_=IQ.TYPE.RESULT)
        return ET.tostring(res)

    async def handle_result(self, _, __):
        """
        Result stanza from client. Safe to ignore
        """
        return

    async def _roster_memory_insert(self, jid, id_roster, item):
        async with self._lock:
            if jid not in self._roster_in_memory:
                self._roster_in_memory[jid] = []

            self._roster_in_memory[jid].append(
                {"id": id_roster, "roster_item": item}
            )

    async def _roster_memory_update(self, jid, id_roster, item):
        async with self._lock:
            if jid in self._roster_in_memory:
                index = next(
                    (index for (index, d) in enumerate(self._roster_in_memory)
                     if d["id"] == id_roster), None
                )
                if index:
                    self._roster_in_memory[jid][index]["roster_item"] = item

    async def _roster_memory_delete(self, jid, id_roster):
        async with self._lock:
            if jid in self._roster_in_memory:
                index = next(
                    (index for (index, d) in enumerate(self._roster_in_memory)
                     if d["id"] == id_roster), None
                )
                if index:
                    self._roster_in_memory[jid].pop(index)

    async def _load_roster_in_memory(self):
        """
        Clears the roster in memory and loads
        from the database.
        Used on startup of Roster
        """
        async with await DB.connection_async() as con:
            query = select(
                Model.Roster.c.id,
                Model.Roster.c.jid,
                Model.Roster.c.roster_item
            )
            res = await con.execute(query)
            res = res.fetchall()

        async with self._lock:
            self._roster_in_memory.clear()
            for id_roster, jid, roster_item in res:
                if jid not in self._roster_in_memory:
                    self._roster_in_memory[jid] = []
                self._roster_in_memory[jid].append(
                    {"id": id_roster, "roster_item": roster_item}
                )

    async def roster_by_jid(self, jid: JID):
        async with self._lock:
            jid = jid.user if jid.domain == AppConfig.app_config.host else jid.bare()
            return self._roster_in_memory.get(jid) or []

    @staticmethod
    async def _store_pending_sub(to_jid: str, item: ET.Element) -> None:
        async with await DB.connection_async() as con:
            query = insert(Model.PendingSubs).values(
                {"jid": to_jid, "item": ET.tostring(item).decode()}
            )
            await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

    @staticmethod
    async def _delete_item_from_database(jid, id_roster):
        async with await DB.connection_async() as con:
            query = delete(Model.Roster).where(
                and_(
                    Model.Roster.c.jid == jid,
                    Model.Roster.c.id == id_roster
                )
                .returning(Model.Roster.c.roster_item)
            )
            await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

    @staticmethod
    async def _update_item_from_database(jid, id_roster, new_item ):
        async with await DB.connection_async() as con:
            query = (
                update(Model.Roster)
                .where(
                    and_(
                        Model.Roster.c.jid == jid,
                        Model.Roster.c.id == id_roster
                    )
                )
                .values({"roster_item": ET.tostring(new_item).decode()})
                .returning(Model.Roster.c.roster_item)
            )
            res = await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

            return res.scalar()

    @staticmethod
    async def _create_item_into_database(jid, new_item):
        async with (await DB.connection_async() as con):
            query = (
                insert(Model.Roster).values(
                    {"jid": jid, "roster_item": ET.tostring(new_item).decode()}
                )
                .returning(Model.Roster.c.id, Model.Roster.c.roster_item)
            )
            res = await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

            res = res.first()
            if res:
                id_res, item_res = res
                return id_res, item_res

            return None
