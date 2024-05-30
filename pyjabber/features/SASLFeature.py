import base64
import hashlib

from contextlib import closing
from enum import Enum
from typing import Tuple, Union
from xml.etree import ElementTree as ET

from pyjabber.db.database import connection
from pyjabber.features.FeatureInterface import FeatureInterface
from pyjabber.network.ConnectionsManager import ConectionsManager
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.utils import ClarkNotation as CN


class mechanismEnum(Enum):
    PLAIN       = "PLAIN"
    SCRAM_SHA_1 = "SCRAM-SHA-1"


class Signal(Enum):
    RESET   = 0
    DONE    = 1


class SASL(FeatureInterface):
    def __init__(self):
        self._handlers = {
            "iq"    : self.handleIQ,
            "auth"  : self.handleAuth
        }
        self._ns = "jabber:iq:register"
        self._connections = ConectionsManager()
        self._peername = None

    def feed(self, element: ET, extra: dict[str, any] = None) -> Union[Tuple[Signal, bytes], bytes]:
        if extra and "peername" in extra.keys():
            self._peername = extra["peername"]

        _, tag = CN.deglose(element.tag)
        return self._handlers[tag](element)

    def handleIQ(self, element: ET.Element) -> Union[Tuple[Signal, bytes], bytes]:
        query = element.find(CN.clarkFromTuple((self._ns, "query")))
        
        if query is None:
            raise Exception()
        
        if element.attrib["type"] == "get":
            pass #TODO XEP-0077 form data

        elif element.attrib["type"] == "set":
            new_jid     = query.find(CN.clarkFromTuple((self._ns, "username"))).text

            with closing(connection()) as con:
                res = con.execute("SELECT * FROM credentials WHERE jid = ?", (new_jid,))
                credentials = res.fetchone()

            if credentials:
                return Signal.RESET, SE.conflict_error(element.attrib["id"])
            else:
                pwd         = query.find(CN.clarkFromTuple((self._ns, "password"))).text
                hash_pwd    = hashlib.sha256(pwd.encode()).hexdigest()

                with closing(connection()) as con:
                    con.execute("INSERT INTO credentials(jid, hash_pwd) VALUES (?, ?)", (new_jid, hash_pwd))
                    con.commit()
                return Signal.RESET, self.iq_register_result(element.attrib["id"])
            
        else:
            raise Exception()


    def handleAuth(self, element: ET.Element) -> Union[Tuple[Signal, bytes], bytes]:
        data    = base64.b64decode(element.text).split("\x00".encode())
        jid     = data[1].decode()
        keyhash = hashlib.sha256(data[2]).hexdigest()

        with closing(connection()) as con:
            res = con.execute("SELECT hash_pwd FROM credentials WHERE jid = ?", (jid,))
            hash_pwd = res.fetchone()

        if hash_pwd:
            if hash_pwd[0] == keyhash:
                self._connections.set_jid(self._peername, jid)
                return Signal.RESET, "<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>".encode()
            
            elem = ET.Element("success", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
            return ET.tostring(elem)
            
        return SE.not_authorized()

    def iq_register_result(self, id: str) -> bytes:
        iq = ET.Element("iq", attrib = {"type": "result", "id": id, "from": "localhost"})
        return ET.tostring(iq)

def SASLFeature(
        mechanismList: list[mechanismEnum] = [
            mechanismEnum.PLAIN
        ]):

    element = ET.Element(
        "mechanisms",
        attrib  = {
            "xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"
        }
    )

    for m in mechanismList:
        mechanism       = ET.SubElement(element, "mechanism")
        mechanism.text  = m.value

    return element
