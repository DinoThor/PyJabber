import asyncio
import xml.etree.ElementTree as ET
from typing import Union

from sqlalchemy import and_, delete, insert, select, update

from pyjabber import AppConfig
from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.plugins.roster.types import RosterInMemory
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
    _roster_in_memory: dict[str, list[RosterInMemory]] = {}
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
        roster = await self._roster_memory_get(jid)

        iq = IQ(type_=IQ.TYPE.RESULT, id_=element.attrib.get("id"))
        query = ET.SubElement(iq, "{jabber:iq:roster}query")

        for item in roster:
            query.append(ET.fromstring(item["roster_item"]))

        return ET.tostring(iq)

    async def handle_set(self, jid: JID, element: ET.Element):
        query = element.find("{jabber:iq:roster}query")
        if query is None:
            return SE.invalid_xml()

        new_item = query.findall("{jabber:iq:roster}item")

        if len(new_item) != 1:
            return SE.invalid_xml()

        new_item = new_item[0]

        roster = await self._roster_memory_get(jid)
        if roster:
            match_entry = next(
                (
                    e for e in roster
                    if ET.fromstring(e["roster_item"]).get("jid")
                    == new_item.attrib.get("jid")
                 ), None
            )
            if match_entry:
                if new_item.attrib.get("subscription") == "remove":
                    await self._delete_item_from_database(jid, match_entry["id"])
                    await self._roster_memory_delete(jid, match_entry["id"])
                else:
                    updated_item = await self._update_item_from_database(
                        jid, match_entry["id"], new_item
                    )
                    await self._roster_memory_update(jid, match_entry["id"], updated_item)
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

    async def roster_by_jid(self, jid: JID):
        """
        Searches and returns the full roster for a given JID
        """
        roster = await self._roster_memory_get(jid)
        return [v.get("roster_item") for v in roster or []]

    async def search_contact(self, jid: JID, to: str) -> Union[tuple[str, ET.Element], None]:
        """
        Search an entry for the contact <to> into the roster of <jid>.
        """
        roster = await self._roster_memory_get(jid)
        match_entry = next(
            (e for e in roster if ET.fromstring(e["roster_item"]).get("jid") == to),
            None,
        )
        if match_entry:
            return match_entry["id"], ET.fromstring(match_entry["roster_item"])
        else:
            return None

    async def search_and_create_contact(self, jid: JID, to: str) -> Union[tuple[str, ET.Element], None]:
        """
        Search an entry for the contact <to> into the roster of <jid>.
        If <to> is not present in the roster, a new entry will be created
        with an empty roster item (subscription=none)
        """
        match_entry = await self.search_contact(jid, to)
        if match_entry:
            return match_entry
        else:
            new_item = ET.Element(
                "{jabber:iq:roster}item", attrib={"jid": to, "subscription": "none"}
            )
            database_id, database_item = await self._create_item_into_database(
                jid, new_item
            )
            await self._roster_memory_insert(jid, database_id, database_item)
            return database_id, new_item

    async def update_contact(self, jid: JID, contact_id: str, new_item: str):
        item = await self._update_item_from_database(jid, contact_id, new_item)
        if item:
            await self._roster_memory_update(jid, contact_id, item)

    async def _roster_memory_get(self, jid: JID):
        async with self._lock:
            try:
                return self._roster_in_memory[jid.bare()]
            except KeyError:
                self._roster_in_memory[jid.bare()] = []
                return []

    async def _roster_memory_insert(self, jid:JID, id_roster: str, item: str):
        async with self._lock:
            try:
                self._roster_in_memory[jid.bare()].append(
                    {"id": id_roster, "roster_item": item}
                )
            except KeyError:
                self._roster_in_memory[jid.bare()] = [
                    {"id": id_roster, "roster_item": item}
                ]

    async def _roster_memory_update(self, jid: JID, id_roster: str, item: str):
        async with self._lock:
            if jid.bare() in self._roster_in_memory:
                index = next(
                    (index for (index, d)
                     in enumerate(self._roster_in_memory[jid.bare()])
                     if d["id"] == id_roster), None
                )
                if index is not None:
                    self._roster_in_memory[jid.bare()][index]["roster_item"] = item

    async def _roster_memory_delete(self, jid: JID, id_roster: str):
        async with self._lock:
            if jid.bare() in self._roster_in_memory:
                index = next(
                    (index for (index, d) in enumerate(self._roster_in_memory)
                     if d["id"] == id_roster), None
                )
                if index:
                    self._roster_in_memory[jid.bare()].pop(index)

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

    @staticmethod
    async def _delete_item_from_database(jid: JID, id_roster):
        async with await DB.connection_async() as con:
            query = delete(Model.Roster).where(
                and_(
                    Model.Roster.c.jid == jid.bare(),
                    Model.Roster.c.id == id_roster
                )
                .returning(Model.Roster.c.roster_item)
            )
            await con.execute(query)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

    @staticmethod
    async def _update_item_from_database(jid: JID, id_roster, new_item):
        async with await DB.connection_async() as con:
            query = (
                update(Model.Roster)
                .where(
                    and_(
                        Model.Roster.c.jid == jid.bare(),
                        Model.Roster.c.id == id_roster
                    )
                )
                .values({"roster_item": ET.tostring(new_item).decode()})
                .returning(Model.Roster.c.roster_item)
            )
            try:
                res = await con.execute(query)
            except Exception as e:
                print(1)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

            return res.first()[0]

    @staticmethod
    async def _create_item_into_database(jid: JID, new_item):
        async with (await DB.connection_async() as con):
            query = (
                insert(Model.Roster).values(
                    {"jid": jid.bare(), "roster_item": ET.tostring(new_item).decode()}
                )
                .returning(Model.Roster.c.id, Model.Roster.c.roster_item)
            )
            try:
                res = await con.execute(query)
            except Exception as e:
                print(e)
            if not AppConfig.app_config.database_in_memory:
                await con.commit()

            res = res.first()
            if res:
                id_res, item_res = res
                return id_res, item_res

            return None
