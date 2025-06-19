import base64
import bcrypt

from enum import Enum
from typing import Dict, List, Tuple, Union
from uuid import uuid4
from xml.etree import ElementTree as ET

from loguru import logger
from sqlalchemy import insert, select

from pyjabber import metadata
from pyjabber.db.model import Model
from pyjabber.db.database import DB
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.stream.Signal import Signal
from pyjabber.utils import ClarkNotation as CN, Singleton


class MECHANISM(Enum):
    PLAIN = "PLAIN"
    SCRAM_SHA_1 = "SCRAM-SHA-1"
    EXTERNAL = "EXTERNAL"


class SASL(metaclass=Singleton):
    """
        SASL Class.

        An instance of this class will manage the authentication from new connections,
        during the stream negotiation process.
    """
    def __init__(self, from_claim = None):
        self._handlers = {
            "iq": self.handleIQ,
            "auth": self.handleAuth
        }
        self._connection_manager = ConnectionManager()
        self._peername = None
        self._from_claim = from_claim

    def feed(self,
             element: ET,
             extra: Dict = None) -> Union[Tuple[Signal, bytes], bytes]:
        if extra and "peername" in extra.keys():
            self._peername = extra["peername"]

        _, tag = CN.deglose(element.tag)
        return self._handlers[tag](element)

    @staticmethod
    def iq_register_result(iq_id: str) -> bytes:
        iq = ET.Element(
            "iq",
            attrib={
                "type": "result",
                "id": iq_id or str(uuid4()),
                "from": metadata.HOST})
        return ET.tostring(iq)

    def handleIQ(self, element: ET.Element) -> bytes:
        query = element.find("{jabber:iq:register}query")

        if query is None:
            return SE.bad_request()

        if element.attrib.get("type") == IQ.TYPE.SET.value:
            new_jid = query.find("{jabber:iq:register}username")

            if new_jid is None:
                return SE.bad_request()

            new_jid = new_jid.text

            with DB.connection() as con:
                query_db = select(Model.Credentials).where(Model.Credentials.c.jid == new_jid)
                credentials = con.execute(query_db).fetchone()

                if credentials:
                    return SE.conflict_error(element.attrib["id"])
                else:
                    pwd = query.find("{jabber:iq:register}password").text
                    hashed_pwd = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())

                    query_insert = insert(Model.Credentials).values({"jid": new_jid, "hash_pwd": hashed_pwd})
                    con.execute(query_insert)
                    con.commit()

            return self.iq_register_result(element.attrib["id"])

        elif element.attrib.get("type") == IQ.TYPE.GET.value:
            iq = IQ(
                type_=IQ.TYPE.RESULT,
                id_=element.attrib["id"] if "id" in element.attrib.keys() else None,
            )
            query = ET.Element('{jabber:iq:register}query')
            ET.SubElement(query, "username")
            ET.SubElement(query, "password")
            iq.append(query)

            return ET.tostring(iq)

    def handleAuth(self, element: ET.Element) -> Union[Tuple[Signal, bytes], bytes]:
        mechanism = element.attrib.get("mechanism")

        if mechanism == MECHANISM.EXTERNAL.value:
            if not self._from_claim:
                raise Exception()  # TODO: handler error properly

            cert = self._connection_manager.get_connection_certificate_server(self._peername)
            if not cert:
                logger.error(f"Error retrieving TLS cert from {self._peername}. Closing connection for server safety")
                self._connection_manager.close(self._peername)

            if not self.validate_cert(self._from_claim, cert):
                logger.error(f"Host claim cannot be verified with presented cert. Verify host used on stream or cert: {self._peername}")
                self._connection_manager.close(self._peername)

            return Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"

        try:
            data = base64.b64decode(element.text).split("\x00".encode())
            jid = data[1].decode()
            pwd = data[2]

            with DB.connection() as con:
                query = select(Model.Credentials.c.hash_pwd).where(Model.Credentials.c.jid == jid)
                hashed_pwd = con.execute(query).fetchone()

            if hashed_pwd and bcrypt.checkpw(pwd, hashed_pwd[0]):
                self._connection_manager.set_jid(self._peername, JID(user=jid, domain=metadata.HOST))
                return Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"
            else:
                return SE.not_authorized()

        except Exception as e:
            logger.error(f"Exception during auth process for {element.attrib.get('from')}: {e}")
            return SE.not_authorized()

    @staticmethod
    def validate_cert(from_claim, cert):
        peer_cert = cert.getpeercert()
        cert_names = []

        subject = peer_cert.get("subject", [])
        for attr in subject:
            for (key, value) in attr:
                if key == "commonName":
                    cert_names.append(value)

        for typ, value in peer_cert.get("subjectAltName", []):
            if typ == "DNS":
                cert_names.append(value)

        return from_claim in cert_names


def SASLFeature(mechanism_list: List[MECHANISM] = None) -> ET.Element:
    """
    SASL    Feature Stream message.

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
