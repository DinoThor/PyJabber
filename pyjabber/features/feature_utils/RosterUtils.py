import xml.etree.ElementTree as ET
from contextlib import closing
from typing import List

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
    return res[0]
