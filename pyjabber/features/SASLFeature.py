import base64
from enum import Enum
import hashlib
import sqlite3
import pyjabber.utils.ClarkNotation as CN
from typing import Tuple
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from pyjabber.features.FeatureInterface import FeatureInterface
from pyjabber.network.ConnectionsManager import ConectionsManager


class mechanismEnum(Enum):
    PLAIN       = "PLAIN"
    SCRAM_SHA_1 = "SCRAM-SHA-1"

class Signal(Enum):
    RESET   = 0
    DONE    = 1


# if "iq" in elem.tag:

#     query = elem.find(CN.clarkFromTuple(("jabber:iq:register", "query")))
#     if query is None:
#         raise Exception()

#     new_jid = query.find(CN.clarkFromTuple(("jabber:iq:register", "username"))).text

#     with sqlite3.connect("./pyjabber/db/server.db") as con:
#         res = con.execute("SELECT jid FROM credentials WHERE jid = ?", (new_jid,))

#     jid_match = res.fetchone()
#     if jid_match is None:
#         pwd         = query.find(CN.clarkFromTuple(("jabber:iq:register", "password"))).text
#         hash_pwd    = hashlib.sha256(pwd.encode()).hexdigest()
        
#         with sqlite3.connect("./pyjabber/db/server.db") as con:
#             con.execute("INSERT INTO credentials(jid, hash_pwd) VALUES(?, ?)", (new_jid, hash_pwd))
#             con.commit()

#         self._buffer.write(IBR.result(elem.attrib["id"]))

#     else:
#         self._buffer.write(IBR.conflict_error(elem.attrib["id"]))                    
    
# if "auth" in elem.tag:

#     data        = base64.b64decode(elem.text).split("\x00".encode())
#     self._jid   = data[1].decode()
#     keyhash     = hashlib.sha256(data[2]).hexdigest()

#     with sqlite3.connect("./pyjabber/db/server.db") as con:
#         res = con.execute("SELECT hash_pwd FROM credentials WHERE jid = ?", (self._jid,))

#     try:
#         hash_pwd = res.fetchone()[0]
#         if hash_pwd == keyhash:
#             self._buffer.write(SASLFeature().success())
#             self._stage = Stage.AUTH

#         else:
#             self._buffer.write(SASLFeature().not_authorized())

#     except (KeyError, TypeError):
#         self._buffer.write(SASLFeature().not_authorized())

#     return Signal.RESET





class SOSLFeature(FeatureInterface):
    def __init__(self):
        self._handlers = {
            "iq"    : self.handleIQ,
            "auth"  : self.handleAuth
        }

    def feed(self, element: ET) -> Tuple[Signal, bytes] | bytes:
        _, tag = CN.deglose(element.tag)
        return self._handlers[tag](element)

    def handleIQ(self, element: ET.Element) -> Tuple[Signal, bytes] | bytes:

        query = element.find(CN.clarkFromTuple(("jabber:iq:register", "query")))
        if query is None:
            raise Exception()

        new_jid     = query.find(CN.clarkFromTuple(("jabber:iq:register", "username"))).text

        with sqlite3.connect("./pyjabber/db/server.db") as con:
            res = con.execute("SELECT * FROM credentials WHERE jid = ?", (new_jid,))

        credentials = res.fetchone()
        if credentials:
            return Signal.RESET, self.conflict_error(element.attrib["id"])
        
        else:
            pwd         = query.find(CN.clarkFromTuple(("jabber:iq:register", "password"))).text
            hash_pwd    = hashlib.sha256(pwd.encode()).hexdigest()

            with sqlite3.connect("./pyjabber/db/server.db") as con:
                con.execute("INSERT INTO credentials(jid, hash_pwd) VALUES (?, ?)", (new_jid, hash_pwd))
                con.commit()

            return Signal.RESET, self.iq_register_result(element.attrib["id"])


    def handleAuth(self, element: ET.Element):
        data    = base64.b64decode(element.text).split("\x00".encode())
        jid     = data[1].decode()
        keyhash = hashlib.sha256(data[2]).hexdigest()

        with sqlite3.connect("./pyjabber/db/server.db") as con:
            res = con.execute("SELECT hash_pwd FROM credentials WHERE jid = ?", (jid,))

        try:
            hash_pwd = res.fetchone()[0]
            if hash_pwd == keyhash:
                return Signal.RESET, self.success()

            else:
                return self.not_authorized()

        except (KeyError, TypeError):
            return self.not_authorized()

    def success(self) -> bytes:
        elem = Element("success", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        return ET.tostring(elem)
    
    def not_authorized(self) -> bytes:
        elem    = Element("failure", attrib = {"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        elem = ET.SubElement(elem, "not-authorized")
        # forbid  = Element("not-authorized")
        # elem.append(forbid)
        return ET.tostring(elem)
    
    def conflict_error(self, id: str):
        return f"<iq id='{id}' type='error' from='localhost'><error type='cancel'><conflict xmlns='urn:ietf:params:xml:ns:xmpp-stanzas' /><text xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'>The requested username already exists.</text></error></iq>".encode()

    def iq_register_result(self, id: str):
        return f"<iq type='result' id='{id}' from='localhost'/>".encode()

class SASLFeature(ET.Element):
    
    def __init__(
            self, 
            tag         : str = "mechanisms", 
            attrib      : dict[str, str] = {
                "xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"
            },
            mechanism   : list[mechanismEnum] = [mechanismEnum.PLAIN],
            **extra : str) -> None:
        
        super().__init__(tag, attrib, **extra)

        for m in mechanism:
            mechanism       = Element("mechanism")
            mechanism.text  = m.value
            self.append(mechanism)        

    def success(self) -> bytes:
        elem = Element("success", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        return ET.tostring(elem)
    
    def not_authorized(self) -> bytes:
        elem    = Element("failure", attrib = {"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        forbid  = Element("not-authorized")
        elem.append(forbid)
        return ET.tostring(elem)
            