from plugins.PluginInterface import Plugin

import xml.etree.ElementTree as ET
import sqlite3

class Roster(Plugin):
    DB_NAME = "./plugins/roster/roster.db"

    def __init__(self) -> None:
        self._handlers = {
            "get": self.handleGet,
            "set": self.handleSet,
        }
        self._ns = "jabber:iq:roster"

        try:
            con = sqlite3.connect(self.DB_NAME)
            cur = con.cursor()
            res = cur.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'roster'")
            if res.fetchone() is None:
                cur.execute("CREATE TABLE roster(jid, rosterList)")
        except:
            pass
        finally:
            cur.close()
            con.close()

    
    def feed(self, jid: str, element: ET.Element):
        if len(element) != 1:
            raise Exception()   #Malformed XML
        
        res = self._handlers[element.attrib["type"]](element, jid)
        return res

    def handleGet(self, element: ET.Element, jid):
        try:
            con = sqlite3.connect(self.DB_NAME)
            cur = con.cursor()
            res = cur.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
            rosters = res.fetchall()
            if len(rosters) == 0:
                res = ET.Element(
                    "iq",
                    attrib = {
                        "id": element.attrib["id"],
                        "to": jid,
                        "type": "result"
                    }
                )
                query = ET.Element("query", attrib = { "xmlns": self._ns })
                res.append(query)
            else:
                pass
        except:
            pass
        finally:
            cur.close()
            con.close()
            return ET.tostring(res)

    def handleSet(self, element):
        pass

    def handleResult(self, element):
        pass