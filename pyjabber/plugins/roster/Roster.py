from enum import Enum
import xml.etree.ElementTree as ET
from contextlib import closing

from pyjabber.db.database import connection
from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ


class subscriptionType(Enum):
    NONE    = "none"
    TO      = "to"
    FROM    = "from"
    BOTH    = "both"


class Roster(Plugin):
    def __init__(self, db_connection_factory) -> None:
        self._handlers = {
            "get"   : self.handleGet,
            "set"   : self.handleSet,
            "result": self.handleResult
        }
        self._ns = {
            "ns"    : "jabber:iq:roster",
            "query" : "{jabber:iq:roster}query",
            "item"  : "{jabber:iq:roster}item"
        }
        self._db_connection_factory = db_connection_factory

    def retriveRoster(self, jid: str):
        with closing(self._db_connection_factory()) as con:
            res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
            roster = res.fetchall()
        return roster

    def update(self, id: int, item: ET.Element) -> str:
        with closing(self._db_connection_factory()) as con:
            con.execute("UPDATE roster SET rosterItem = ? WHERE id = ?", (ET.tostring(item).decode(), id))
            con.commit()
            res = con.execute("SELECT rosterItem from roster WHERE id = ?", (id, ))
            res = res.fetchone()

        return res[0]

    def feed(self, jid: str, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        return self._handlers[element.attrib["type"]](element, jid)


    ############################################################
    ############################################################


    def handleGet(self, element: ET.Element, jid):
        jid = jid.split("/")[0]
        try:
            with closing(self._db_connection_factory()) as con:
                res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
                roster = res.fetchall()

            iq_res = IQ(
                type = IQ.TYPE.RESULT.value,
                id = element.attrib["id"]
            )

            query = ET.SubElement(
                iq_res,
                "query",
                attrib = {"xmlns": self._ns["ns"]}
            )

            for item in roster:
                query.append(ET.fromstring(item[-1]))

            return ET.tostring(iq_res)

        except:
            raise Exception()


    def handleSet(self, element: ET.Element, jid: str):
        query   = element.find(self._ns["query"])
        jid     = jid.split("/")[0]

        if query is None:
            raise Exception()

        new_item = query.findall(self._ns["item"])

        if len(new_item) != 1:
            raise Exception()

        new_item    = new_item[0]
        if "subscription" in new_item.attrib.keys():
            remove = new_item.attrib["subscription"] == "remove"

        with closing(connection()) as con:
            res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
            res = res.fetchall()

        roster      = res
        roster      = [ET.fromstring(r[-1]) for r in roster]
        match_item  = [i for i in roster if i.attrib["jid"] == new_item.attrib["jid"]]

        if match_item:
            # Delete roster item
            if remove:
                with closing(connection()) as con:
                    con.execute("""
                                DELETE FROM roster
                                WHERE jid = ? AND rosterItem = ?
                                """,
                                (jid,
                                 ET.tostring(match_item[0]).decode()))
                    con.commit()

            else:
                # Update roster item
                with closing(connection()) as con:
                    con.execute("""
                                UPDATE roster
                                SET rosterItem = ?
                                WHERE jid = ? AND rosterItem = ?
                                """,
                                (ET.tostring(new_item).decode(),
                                jid,
                                ET.tostring(match_item[0])))
                    con.commit()

        else:
            # New roster item
            if not remove:
                with closing(connection()) as con:
                    con.execute("INSERT INTO roster(jid, rosterItem) VALUES (?, ?)", (jid, ET.tostring(new_item).decode()))
                    con.commit()

        res = ET.Element(
            "iq",
            attrib = {
                "id"    : element.attrib["id"],
                "type"  : "result"
            }
        )

        return ET.tostring(res)

    def handleResult(self, element: ET.Element, jid: str):
        # It's safe to ignore this stanza
        return
