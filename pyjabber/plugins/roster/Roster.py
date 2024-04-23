import xml.etree.ElementTree as ET
import pyjabber.stanzas.error.StanzaError as SE
import sqlite3

from contextlib import closing
from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.stanzas.IQ import IQ



class Roster(Plugin):
    DB_NAME = "./pyjabber/plugins/roster/roster.db"

    def __init__(self) -> None:
        self._handlers = {
            "get": self.handleGet,
            "set": self.handleSet,
        }
        self._ns = "jabber:iq:roster"

        con = sqlite3.connect(self.DB_NAME)
        res = con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'roster'")

        if res.fetchone() is None:
            try:
                with con:
                    con.execute("CREATE TABLE roster(jid, rosterList)")
            except sqlite3.IntegrityError:
                print("ERROR")

        con.close()

    
    def feed(self, jid: str, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()
        
        return self._handlers[element.attrib["type"]](element, jid)

    def handleGet(self, element: ET.Element, jid):
        try:
            with closing(sqlite3.connect(self.DB_NAME)) as con:
                res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
                rosters = res.fetchall()

                iq_res = IQ(
                    type = IQ.TYPE.ERROR,
                    id = element.attrib["id"]
                )
                print(type(iq_res))
                print("\n\n")
                print(iq_res)
                print("HHHHHHHHHHHHHHHHHHHHH")
                query = ET.Element(
                    "query",
                    attrib = {"xmlns": self._ns}
                )

                if rosters:
                    query.append(ET.fromstring(rosters[0]))                
                
                iq_res.append(query)
                # print(ET.tostring(iq_res))
                return ET.tostring(iq_res)
                
        except Exception as e:
            # print(e)
            pass


    def handleSet(self, element):
        pass

    def handleResult(self, element):
        pass