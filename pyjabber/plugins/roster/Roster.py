import pyjabber.stanzas.error.StanzaError as SE
import pyjabber.utils.ClarkNotation as CN
import xml.etree.ElementTree as ET

from contextlib import closing
from pyjabber.db.database import connection
from pyjabber.plugins.PluginInterface import Plugin
from pyjabber.stanzas.IQ import IQ
from sqlite3 import IntegrityError


class Roster(Plugin):
    def __init__(self) -> None:
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
    
    def feed(self, jid: str, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()
        
        return self._handlers[element.attrib["type"]](element, jid)

    def handleGet(self, element: ET.Element, jid):
        try:
            with closing(connection()) as con:
                res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
                roster = res.fetchone()

            iq_res = IQ(
                type = IQ.TYPE.RESULT.value,
                id = element.attrib["id"]
            )

            query = ET.SubElement(
                iq_res,
                "query",
                attrib = {"xmlns": self._ns["ns"]}
            )

            if roster:
                query.append(ET.fromstring(roster))                
            
            return ET.tostring(iq_res)
                
        except:
            raise Exception()


    def handleSet(self, element: ET.Element, jid: str):
        query = element.find(self._ns["query"])

        if query is None:
            raise Exception()
        
        item = query.findall(self._ns["item"])
        if len(item) != 1:
            raise Exception()
        item = item[0]
        
        with closing(connection()) as con:
            res = con.execute("SELECT * FROM roster WHERE jid = ?", (jid,))
            res = res.fetchone()

        if res is None:
            new_roster = ET.tostring(item).decode()
            print(new_roster)
            with closing(connection()) as con:
                con.execute("INSERT INTO roster(jid, rosterList) VALUES (?, ?)", (jid, new_roster))
                con.commit()

        roster = ET.fromstring(res)

        print(res); return
        roster = ET.fromstring(res)
        print(roster); return
        print(ET.tostring(roster))
        

    def handleResult(self, element):
        pass