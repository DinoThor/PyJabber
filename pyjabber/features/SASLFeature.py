import base64
import hashlib
from contextlib import closing
from enum import Enum
from typing import Dict, List, Tuple, Union
from uuid import uuid4
from xml.etree import ElementTree as ET

from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.metadata import host
from pyjabber.db.database import connection
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import ClarkNotation as CN, Singleton


class MECHANISM(Enum):
    PLAIN = "PLAIN"
    SCRAM_SHA_1 = "SCRAM-SHA-1"
    EXTERNAL = "EXTERNAL"


class Signal(Enum):
    RESET = 0
    DONE = 1


def iq_register_result(iq_id: str) -> bytes:
    iq = ET.Element(
        "iq",
        attrib={
            "type": "result",
            "id": iq_id or str(uuid4()),
            "from": host.get()})
    return ET.tostring(iq)


class SASL(metaclass=Singleton):
    """
        SASL Class.

        An instance of this class will manage the authentication from new connections,
        during the stream negotiation process.

        :param db_connection_factory: The DB connection object used to look up the credentials

    """

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
             extra: Dict = None) -> Union[Tuple[Signal, bytes], bytes]:
        if extra and "peername" in extra.keys():
            self._peername = extra["peername"]

        _, tag = CN.deglose(element.tag)
        return self._handlers[tag](element)

    def handleIQ(
        self, element: ET.Element) -> Union[Tuple[Signal, bytes], bytes]:
        query = element.find("{jabber:iq:register}query")

        if query is None:
            return SE.bad_request()

        if element.attrib["type"] == IQ.TYPE.SET.value:
            new_jid = query.find("{jabber:iq:register}username")

            if new_jid is None:
                return SE.bad_request()

            new_jid = new_jid.text

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
                    return iq_register_result(
                        element.attrib["id"])

        elif element.attrib["type"] == "get":
            iq = IQ(
                type_=IQ.TYPE.RESULT,
                id_=element.attrib["id"] if "id" in element.attrib.keys() else None,
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
        key_hash = hashlib.sha256(data[2]).hexdigest()

        with closing(self._db_connection_factory()) as con:
            res = con.execute(
                "SELECT hash_pwd FROM credentials WHERE jid = ?", (jid,))
            hash_pwd = res.fetchone()

        if hash_pwd and hash_pwd[0] == key_hash:
            self._connection_manager.set_jid(self._peername, JID(user=jid, domain=host.get()))
            return Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"

        return SE.not_authorized()


def SASLFeature(mechanism_list: List[MECHANISM] = None) -> ET.Element:
    """
    SASL Feature Stream message.

    Indicates to the client the methods available to authenticate.

    :param mechanism_list: List of Mechanism selected for the stream session. Default is PLAIN
    """
    mechanism_list = mechanism_list or [MECHANISM.PLAIN]

    element = ET.Element(
        "mechanisms",
        attrib={
            "xmlns": "urn:ietf:params:xml:ns:xmpp-sasl"
        }
    )

    for m in mechanism_list:
        mechanism = ET.SubElement(element, "mechanism")
        mechanism.text = m.value

    return element
