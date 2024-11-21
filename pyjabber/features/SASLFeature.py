import base64
import hashlib
from contextlib import closing
from enum import Enum
from typing import Dict, List, Tuple, Union
from xml.etree import ElementTree as ET

from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.db.database import connection
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.utils import ClarkNotation as CN


class mechanismEnum(Enum):
    PLAIN = "PLAIN"
    SCRAM_SHA_1 = "SCRAM-SHA-1"
    EXTERNAL = "EXTERNAL"


class Signal(Enum):
    RESET = 0
    DONE = 1


class SASL:
    def __init__(self, db_connection_factory=connection):
        self._handlers = {
            "iq": self.handleIQ,
            "auth": self.handleAuth
        }
        self._ns = "jabber:iq:register"
        self._connection_manager = ConnectionManager()
        self._db_connection_factory = db_connection_factory
        self._peername = None

    def feed(self,
             element: ET,
             extra: Dict[str,
                         any] = None) -> Union[Tuple[Signal,
                                                     bytes],
                                               bytes]:
        if extra and "peername" in extra.keys():
            self._peername = extra["peername"]

        _, tag = CN.deglose(element.tag)
        return self._handlers[tag](element)

    def handleIQ(
            self, element: ET.Element) -> Union[Tuple[Signal, bytes], bytes]:
        query = element.find(CN.clarkFromTuple((self._ns, "query")))

        if query is None:
            raise Exception()

        if element.attrib["type"] == "set":
            new_jid = query.find(
                CN.clarkFromTuple(
                    (self._ns, "username"))).text

            with closing(self._db_connection_factory()) as con:
                res = con.execute(
                    "SELECT * FROM credentials WHERE jid = ?", (new_jid,))
                credentials = res.fetchone()

                if credentials:
                    return SE.conflict_error(
                        element.attrib["id"])
                else:
                    pwd = query.find(
                        CN.clarkFromTuple(
                            (self._ns, "password"))).text
                    hash_pwd = hashlib.sha256(pwd.encode()).hexdigest()

                    con.execute(
                        "INSERT INTO credentials(jid, hash_pwd) VALUES (?, ?)", (new_jid, hash_pwd))
                    con.commit()
                    return self.iq_register_result(
                        element.attrib["id"])

        elif element.attrib["type"] == "get":
            iq = IQ(
                type=IQ.TYPE.RESULT.value,
                id=element.attrib["id"] if "id" in element.attrib.keys() else None,
            )
            query = ET.Element('{jabber:iq:register}query')
            ET.SubElement(query, "username")
            ET.SubElement(query, "password")
            iq.append(query)

            return ET.tostring(iq)

    def handleAuth(
            self, element: ET.Element) -> Union[Tuple[Signal, bytes], bytes]:
        data = base64.b64decode(element.text).split("\x00".encode())
        jid = data[1].decode()
        keyhash = hashlib.sha256(data[2]).hexdigest()

        with closing(self._db_connection_factory()) as con:
            res = con.execute(
                "SELECT hash_pwd FROM credentials WHERE jid = ?", (jid,))
            hash_pwd = res.fetchone()

        if hash_pwd and hash_pwd[0] == keyhash:
            self._connection_manager.set_jid(self._peername, jid)
            return Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"

        return SE.not_authorized()

    def iq_register_result(self, id: str) -> bytes:
        iq = ET.Element(
            "iq",
            attrib={
                "type": "result",
                "id": id,
                "from": "localhost"})
        return ET.tostring(iq)


def SASLFeature(
        mechanismList: List[mechanismEnum] = [
            mechanismEnum.PLAIN
        ]):
    element = ET.Element(
        "mechanisms",
        attrib={
            "xmlns": "urn:ietf:params:xml:ns:xmpp-sasl"
        }
    )

    for m in mechanismList:
        mechanism = ET.SubElement(element, "mechanism")
        mechanism.text = m.value

    return element
