import base64
from contextlib import closing
import hashlib
import pyjabber.utils.ClarkNotation as CN

from enum import Enum
from pyjabber.features.FeatureInterface import FeatureInterface
from typing import Tuple
from xml.etree import ElementTree as ET
from pyjabber.db.database import connection


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

    def feed(self, element: ET) -> Tuple[Signal, bytes] | bytes:
        _, tag = CN.deglose(element.tag)
        return self._handlers[tag](element)

    def handleIQ(self, element: ET.Element) -> Tuple[Signal, bytes] | bytes:
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
                return Signal.RESET, self.conflict_error(element.attrib["id"])
            else:
                pwd         = query.find(CN.clarkFromTuple((self._ns, "password"))).text
                hash_pwd    = hashlib.sha256(pwd.encode()).hexdigest()

                with closing(connection()) as con:
                    con.execute("INSERT INTO credentials(jid, hash_pwd) VALUES (?, ?)", (new_jid, hash_pwd))
                    con.commit()
                return Signal.RESET, self.iq_register_result(element.attrib["id"])
            
        else:
            raise Exception()


    def handleAuth(self, element: ET.Element) -> Tuple[Signal, bytes] | bytes:
        data    = base64.b64decode(element.text).split("\x00".encode())
        jid     = data[1].decode()
        keyhash = hashlib.sha256(data[2]).hexdigest()

        with closing(connection()) as con:
            res = con.execute("SELECT hash_pwd FROM credentials WHERE jid = ?", (jid,))
            hash_pwd = res.fetchone()

        if hash_pwd:
            if hash_pwd[0] == keyhash:
                return Signal.RESET, self.success()
            
        return self.not_authorized()

    def success(self) -> bytes:
        elem = ET.Element("success", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        return ET.tostring(elem)
    
    def not_authorized(self) -> bytes:
        elem = ET.Element("failure", attrib = {"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
        ET.SubElement(elem, "not-authorized")
        return ET.tostring(elem)
    
    def conflict_error(self, id: str) -> bytes:
        iq = ET.Element("iq", attrib = {"id": id, "type": "error", "from": "localhost"})
        error = ET.SubElement(iq, "error", attrib = {"type": "cancel"})
        ET.SubElement(error, "conflict", attrib = {"xmlns": "urn:ietf:params:xml:ns:xmpp-stanzas"})
        text = ET.SubElement(error, "text", attrib = {"xmlns": "urn:ietf:params:xml:ns:xmpp-stanzas"})
        text.text = "The requested username already exists"
        return ET.tostring(iq)
        # return f"<iq id='{id}' type='error' from='localhost'><error type='cancel'><conflict xmlns='urn:ietf:params:xml:ns:xmpp-stanzas' /><text xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'>The requested username already exists.</text></error></iq>".encode()

    def iq_register_result(self, id: str) -> bytes:
        iq = ET.Element("iq", attrib = {"type": "result", "id": id, "from": "localhost"})
        return ET.tostring(iq)
        # return f"<iq type='result' id='{id}' from='localhost'/>".encode()

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
        mechanism       = ET.Element("mechanism")
        mechanism.text  = m.value
        element.append(mechanism)  

    return element


def success() -> bytes:
    elem = ET.Element("success", attrib={"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
    return ET.tostring(elem)

def not_authorized() -> bytes:
    elem = ET.Element("failure", attrib = {"xmlns" : "urn:ietf:params:xml:ns:xmpp-sasl"})
    ET.SubElement(elem, "not-authorized")
    return ET.tostring(elem)
            