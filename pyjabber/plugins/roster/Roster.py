import xml.etree.ElementTree as ET
from sqlalchemy import select, insert, update, delete, and_

from pyjabber.db.database import DB
from pyjabber import metadata
from pyjabber.db.model import Model
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton


class Roster(metaclass=Singleton):
    """
        Roster plugin.

        Manages the roster list for each registered user in the server.

        A roster in XMPP is a server-stored contact list that manages contacts, presence status,
        and subscription requests.
        It enables real-time presence updates, contact organization, and synchronization across devices,
        ensuring seamless and private communication.
    """

    def __init__(self) -> None:
        self._handlers = {
            "get": self.handle_get,
            "set": self.handle_set,
            "result": self.handle_result
        }

        self._roster_in_memory = {}
        self._update_roster()

    def feed(self, jid: JID, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        return self._handlers[element.attrib.get("type")](jid, element)

    def handle_get(self, jid: JID, element: ET.Element):
        if jid.domain == metadata.HOST:
            jid = jid.user
        else:
            jid = jid.bare()

        roster = self._roster_in_memory.get(jid)

        iq = IQ(type_=IQ.TYPE.RESULT, id_=element.attrib.get("id"))
        query = ET.SubElement(iq, "query", attrib={"xmlns": "jabber:iq:roster"})

        for item in roster or []:
            query.append(ET.fromstring(item.get("item")))

        return ET.tostring(iq)

    def handle_set(self, jid: JID, element: ET.Element):
        query = element.find("{jabber:iq:roster}query")
        if query is None:
            return SE.invalid_xml()

        jid = jid.user if jid.domain == metadata.HOST else jid.bare()
        new_item = query.findall("{jabber:iq:roster}item")

        if len(new_item) != 1:
            return SE.invalid_xml()

        new_item = new_item[0]

        roster = self._roster_in_memory.get(jid)
        if roster:
            match_item = [i for i in roster if ET.fromstring(i.get("item")).get("jid") == new_item.attrib.get("jid")]
            if match_item:  # UPDATE EXISTING ENTRY
                match_item = match_item[0]
                if new_item.attrib.get("remove") == "remove":  # DELETE ENTRY
                    with DB.connection() as con:
                        query = delete(Model.Roster).where(
                            and_(
                                Model.Roster.c.jid == jid,
                                Model.Roster.c.roster_item == ET.tostring(match_item.get("item")).decode()
                            )
                        )
                        con.execute(query)
                        con.commit()

                else:  # UPDATE FIELDS OF ENTRY
                    with DB.connection() as con:
                        query = update(Model.Roster).where(
                            and_(
                                Model.Roster.c.jid == jid,
                                Model.Roster.c.roster_item == match_item.get("item")
                            )
                        ).values({"roster_item": ET.tostring(new_item).decode()})
                        con.execute(query)
                        con.commit()

            else:  # CREATE NEW ENTRY
                if new_item.attrib.get("remove") != "remove":
                    with DB.connection() as con:
                        query = insert(Model.Roster).values({
                            "jid": jid,
                            "roster_item": ET.tostring(new_item).decode()
                        })
                        con.execute(query)
                        con.commit()

        else:
            with DB.connection() as con:
                query = insert(Model.Roster).values({
                    "jid": jid,
                    "roster_item": ET.tostring(new_item).decode()
                })
                con.execute(query)
                con.commit()

        self._update_roster()
        res = IQ(
            id_=element.attrib.get("id"),
            type_=IQ.TYPE.RESULT
        )
        return ET.tostring(res)

    def handle_result(self, _, __):
        # It's safe to ignore this stanza
        return

    def create_roster_entry(self, jid: JID,  to: JID):
        iq = IQ(
            from_=str(jid),
            type_=IQ.TYPE.SET
        )
        query = ET.SubElement(iq, "{jabber:iq:roster}query")
        if to.domain == metadata.HOST:
            ET.SubElement(query, "{jabber:iq:roster}item", attrib={"jid": to.user, "subscription": "none"})
        else:
            ET.SubElement(query, "{jabber:iq:roster}item", attrib={"jid": to.bare(), "subscription": "none"})

        return self.feed(jid, iq)

    @staticmethod
    def store_pending_sub(to_: str, item: ET.Element) -> None:
        with DB.connection() as con:
            query = insert(Model.PendingSubs).values({
                "jid": to_,
                "item":  ET.tostring(item).decode()
            })
            con.execute(query)
            con.commit()

    def update_item(self, item: ET.Element, id_: int):
        with DB.connection() as con:
            query = update(Model.Roster).where(Model.Roster.c.id == id_).values({
                "roster_item": ET.tostring(item).decode()
            })
            con.execute(query)
            con.commit()
        self._update_roster()

    def _update_roster(self):
        with DB.connection() as con:
            query = select(
                Model.Roster.c.id,
                Model.Roster.c.jid,
                Model.Roster.c.roster_item
            )
            res = con.execute(query).fetchall()

        self._roster_in_memory.clear()
        for id_, jid, item in res:
            if jid not in self._roster_in_memory:
                self._roster_in_memory[jid] = []
            self._roster_in_memory[jid].append({"id": id_, "item": item})

    def roster_by_jid(self, jid: JID):
        if jid.domain == metadata.HOST:
            return self._roster_in_memory.get(jid.user) or []
        return self._roster_in_memory.get(jid.bare()) or []
