import xml.etree.ElementTree as ET
from contextlib import closing

from pyjabber.db.database import connection
from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ


class Roster(Plugin):
    def __init__(self, jid: str, db_connection_factory=None) -> None:
        self._jid = jid
        self._handlers = {
            "get": self.handle_get,
            "set": self.handle_set,
            "result": self.handle_result
        }
        self._ns = {
            "ns": "jabber:iq:roster",
            "query": "{jabber:iq:roster}query",
            "item": "{jabber:iq:roster}item"
        }
        self._db_connection_factory = db_connection_factory or connection

    def feed(self, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        return self._handlers[element.attrib["type"]](element)

    ############################################################
    ############################################################

    def handle_get(self, element: ET.Element):
        jid = self._jid.split("/")[0]
        try:
            with closing(self._db_connection_factory()) as con:
                res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
                roster = res.fetchall()

            iq_res = IQ(
                type=IQ.TYPE.RESULT.value,
                id=element.attrib["id"]
            )

            query = ET.SubElement(
                iq_res,
                "query",
                attrib={"xmlns": self._ns["ns"]}
            )

            for item in roster:
                query.append(ET.fromstring(item[-1]))

            return ET.tostring(iq_res)

        except:
            raise Exception()

    def handle_set(self, element: ET.Element):
        query = element.find(self._ns["query"])
        jid = self._jid.split("/")[0]

        if query is None:
            raise Exception()

        new_item = query.findall(self._ns["item"])

        if len(new_item) != 1:
            raise Exception()

        new_item = new_item[0]
        if "subscription" in new_item.attrib.keys():
            remove = new_item.attrib["subscription"] == "remove"

        with closing(self._db_connection_factory()) as con:
            res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
            res = res.fetchall()

            roster = res
            roster = [ET.fromstring(r[-1]) for r in roster]
            match_item = [i for i in roster if i.attrib["jid"] == new_item.attrib["jid"]]

            if match_item:
                # Delete roster item
                if remove:
                    con.execute("""
                                DELETE FROM roster
                                WHERE jid = ? AND rosterItem = ?
                                """,
                                (jid,
                                 ET.tostring(match_item[0]).decode()))
                    con.commit()

                else:
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
                if not remove:
                    con.execute("INSERT INTO roster(jid, rosterItem) VALUES (?, ?)",
                                (jid, ET.tostring(new_item).decode()))
                    con.commit()

            res = ET.Element(
                "iq",
                attrib={
                    "id": element.attrib["id"],
                    "type": "result"
                }
            )

            return ET.tostring(res)

    def handle_result(self, element: ET.Element):
        # It's safe to ignore this stanza
        return
