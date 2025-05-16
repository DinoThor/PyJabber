import xml.etree.ElementTree as ET
from contextlib import closing
from typing import List
from uuid import uuid4

from sqlalchemy import select

from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.stream.JID import JID


def retrieve_roster(jid: str) -> List[str]:  # pragma: no cover
    with DB.connection() as con:
        query = select(Model.Roster).where(Model.Roster.c.jid == jid)
        roster = con.execute(query)
    return roster


def update(id: int, item: ET) -> str:  # pragma: no cover
    with DB.connection() as con:
        query = Model.Roster.update().where(Model.Roster.c.id == id).values(rosterItem=ET.tostring(item).decode())
        # con.execute("UPDATE roster SET rosterItem = ? WHERE id = ?",
        #             (ET.tostring(item).decode(), id))
        con.execute(query)
        con.commit()
        retrieve = select(Model.Roster.c.rosterItem).where(Model.Roster.c.id == id)
        # res = con.execute("SELECT rosterItem from roster WHERE id = ?", (id,))
        res = con.execute(retrieve).first()

    return res[0] if res else ""


def store_pending_sub(from_: str, to_: str, item: ET.Element) -> None:
    with DB.connection() as con:
        con.execute("INSERT INTO pendingsub values (?, ?, ?)", (from_, to_, ET.tostring(item).decode()))
        con.commit()


def check_pending_sub() -> List[str]:
    with DB.connection() as con:
        res = con.execute("SELECT * FROM pendingsub")
        pending = res.fetchall()

        con.execute("DELETE FROM pendingsub")
        con.commit()
    return pending


def check_pending_sub_to(jid: str, to: str) -> ET.Element:
    with DB.connection() as con:
        res = con.execute("SELECT * FROM pendingsub WHERE jid_from = ? AND jid_to = ?", (jid, to))
        res = res.fetchone()
    if res:
        return res


def create_roster_entry(jid: JID, to: JID, roster_manager: Roster):
    iq = ET.Element(
        "iq", attrib={"from": str(jid), "id": str(uuid4()), "type": "set"}
    )
    query = ET.Element("{jabber:iq:roster}query")
    item = ET.Element(
        "{jabber:iq:roster}item",
        attrib={
            "jid": str(to),
            "subscription": "none"})
    query.append(item)
    iq.append(query)

    return roster_manager.feed(jid, iq)

