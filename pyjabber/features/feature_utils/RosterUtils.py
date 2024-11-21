import xml.etree.ElementTree as ET
from contextlib import closing
from typing import List
from uuid import uuid4

from pyjabber.db.database import connection


def retrieve_roster(jid: str) -> List[str]:  # pragma: no cover
    with closing(connection()) as con:
        res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
        roster = res.fetchall()
    return roster


def update(id: int, item: ET) -> str:  # pragma: no cover
    with closing(connection()) as con:
        con.execute("UPDATE roster SET rosterItem = ? WHERE id = ?",
                    (ET.tostring(item).decode(), id))
        con.commit()
        res = con.execute("SELECT rosterItem from roster WHERE id = ?", (id,))
        res = res.fetchone()

    if res:
        return res[0]
    else:
        return ""


def store_pending_sub(from_: str, to_: str, item: ET.Element) -> None:
    with closing(connection()) as con:
        con.execute("INSERT INTO pendingsub values (?, ?, ?)", (from_, to_, ET.tostring(item).decode()))
        con.commit()


def check_pending_sub(jid: str) -> List[str]:
    with closing(connection()) as con:
        res = con.execute("SELECT * FROM pendingsub WHERE jid_to = ?", (jid,))
        pending = res.fetchall()

        con.execute("DELETE FROM pendingsub WHERE jid_to = ?", (jid,))
        con.commit()
    return pending


def check_pending_sub_to(jid: str, to: str) -> ET.Element:
    with closing(connection()) as con:
        res = con.execute("SELECT * FROM pendingsub WHERE jid_from = ? AND jid_to = ?", (jid, to))
        res = res.fetchone()
    if res:
        return res


def create_roster_entry(jid, to, roster_manager):
    iq = ET.Element(
        "iq", attrib={"from": jid, "id": str(uuid4()), "type": "set"}
    )
    query = ET.Element("{jabber:iq:roster}query")
    item = ET.Element(
        "{jabber:iq:roster}item",
        attrib={
            "jid": to,
            "subscription": "none"})
    query.append(item)
    iq.append(query)

    return roster_manager.feed(iq)

