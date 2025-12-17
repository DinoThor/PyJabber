import asyncio
import base64
import binascii
import hashlib
import hmac
import os
import string
from concurrent.futures import ThreadPoolExecutor
from functools import partial

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
from pyjabber.stream.Stage import Stage
from pyjabber.utils import ClarkNotation as CN, Singleton


class MECHANISM(Enum):
    PLAIN = "PLAIN"
    SCRAM_SHA_1 = "SCRAM-SHA-1"
    EXTERNAL = "EXTERNAL"


class SASL():
    """
        SASL Class.

        An instance of this class will manage the authentication from new connections,
        during the stream negotiation process.
    """
    def __init__(self, transport, parser, from_claim = None):
        self._handlers = {
            "iq": self.handle_IQ,
            "auth": self.handle_auth
        }
        self._connection_manager = ConnectionManager()
        self._from_claim = from_claim

        self._transport = transport
        self._parser = parser

        self._pool = asyncio.get_running_loop()
        self._pool_executor = ThreadPoolExecutor(max_workers=(os.cpu_count() or 2) + 1, thread_name_prefix="crypto_worker")

    async def feed(self, element: ET, transport, peername) -> Union[Tuple[Signal, bytes], bytes]:

        _, tag = CN.deglose(element.tag)
        return await self._handlers[tag](element)

    @staticmethod
    def iq_register_result(iq_id: str) -> bytes:
        iq = ET.Element(
            "iq",
            attrib={
                "type": "result",
                "id": iq_id or str(uuid4()),
                "from": metadata.HOST})
        return ET.tostring(iq)

    async def handle_IQ(self, element: ET.Element) -> bytes | None:
        query = element.find("{jabber:iq:register}query")

        if query is None:
            return SE.bad_request()

        if element.attrib.get("type") == IQ.TYPE.SET.value:
            new_jid = query.find("{jabber:iq:register}username")
            if new_jid is None:
                self._transport.write(SE.bad_request())

            new_jid = new_jid.text

            async with await DB.connection_async() as con:
                query_db = select(Model.Credentials).where(Model.Credentials.c.jid == new_jid)
                try:
                    credentials = await con.execute(query_db)
                except Exception as e:
                    a = 1
                credentials = credentials.fetchone()

            if credentials:
                self._transport.write(SE.conflict_error(element.attrib.get("id")))
            else:
                pwd = query.find("{jabber:iq:register}password").text
                await self.store_hash_task(self._transport, pwd, new_jid, element.attrib.get("id"))
                self._transport.write(self.iq_register_result(element.attrib["id"]))

        elif element.attrib.get("type") == IQ.TYPE.GET.value:
            iq = IQ(
                type_=IQ.TYPE.RESULT,
                id_=element.attrib["id"] if "id" in element.attrib.keys() else None,
            )
            query = ET.Element('{jabber:iq:register}query')
            ET.SubElement(query, "username")
            ET.SubElement(query, "password")
            iq.append(query)

            self._transport.write(ET.tostring(iq))

        return None

    async def handle_auth(self, element: ET.Element) -> Union[Tuple[Signal, bytes], bytes]:
        mechanism = element.attrib.get("mechanism")

        if mechanism == MECHANISM.EXTERNAL.value:
            if not self._from_claim:
                raise Exception()  # TODO: handler error properly

            cert = self._connection_manager.get_connection_certificate_server(self._transport.get("peername"))
            if not cert:
                logger.error(f"Error retrieving TLS cert from {self._transport.get("peername")}. Closing connection for server safety")
                self._connection_manager.close(self._transport.get("peername"))

            if not self.validate_cert(self._from_claim, cert):
                logger.error(f"Host claim cannot be verified with presented cert. Verify host used on stream or cert: {self._transport.get("peername")}")
                self._connection_manager.close(self._transport.get("peername"))

            return Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"

        try:
            data = base64.b64decode(element.text).split("\x00".encode())
            jid = data[1].decode()
            pwd = data[2].decode()

            async with await DB.connection_async() as con:
                query = select(Model.Credentials.c.hash_pwd).where(Model.Credentials.c.jid == jid)
                hashed_pwd = await con.execute(query)
                hashed_pwd = hashed_pwd.fetchone()

            if not hashed_pwd:
                self._transport.write(SE.not_authorized())

            authorized = await self.verify_password_async(
                stored_password=hashed_pwd[0],
                provided_password=pwd,
                jid_str=jid,
                peername=self._transport.get_extra_info("peername"),
                transport=self._transport
            )
            if authorized:
                self._connection_manager.set_jid(self._transport.get_extra_info("peername"), JID(user=jid, domain=metadata.HOST))
                self._transport.write(b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
                self._parser.reset_stack()
                self._transport.resume_reading()
                return Stage.AUTH
            else:
                self._transport.write(SE.not_authorized())
                self._transport.write(b'</stream:stream>')

        except Exception as e:
            logger.error(f"Exception during auth process for {element.attrib.get('from')}: {e}")
            self._transport.write(SE.not_authorized())

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

    async def store_hash_task(self, transport: asyncio.Transport, password: str, jid_str: str, request_id: string):
        """Handles the full user registration process by hashing the password and storing credentials.

            This coroutine executes the CPU-intensive password hashing and the I/O-bound
            database insertion, ensuring neither operation blocks the main event loop.
            It concludes the registration by sending an XMPP success response to the client.

            Args:
                transport: The asyncio Transport object to communicate with the client.
                password: The user's plain text password to be hashed and stored.
                jid_str: The Jabber ID (JID) of the user being registered.
                request_id: The original XMPP IQ stanza ID, used to form the response.

            Raises:
                Exception: Catches and logs any exceptions that might occur during
                           hashing or database insertion, ensuring the task doesn't
                           crash the server. (Implicit, based on typical async task handling).
        """
        hashed_pwd = await self._hash_scram_async(
            password=password,
            iterations=100000,
            salt=os.urandom(16)
        )

        async with await DB.connection_async() as con:
            query_insert = insert(Model.Credentials).values({"jid": jid_str, "hash_pwd": hashed_pwd})
            await con.execute(query_insert)
            await con.commit()

    async def verify_password_async(self, transport: asyncio.Transport, peername: str, jid_str: str, stored_password: str, provided_password: str) -> bool:
        """
        Verifica una contraseña SÍNCRONAMENTE contra el string almacenado.

        Args:
            stored_password: El string completo de la DB (ej. "sha256$100000$salt_hex$hash_hex").
            provided_password: La contraseña que el usuario intentó ingresar.

        Returns:
            bool: True si las contraseñas coinciden, False en caso contrario.
        """
        try:
            _, iter_str, salt_hex, hash_hex = stored_password.split('$')

            iterations = int(iter_str)
            salt = binascii.unhexlify(salt_hex)

            new_hash = await self._hash_scram_async(provided_password, salt, iterations)
            _, _, _, new_hash = new_hash.split("$")

            return hmac.compare_digest(new_hash, hash_hex)

        except (ValueError, IndexError, binascii.Error):
            # Maneja formatos incorrectos o errores de decodificación
            return False

    async def _hash_scram_async(self, password: str, salt: bytes, iterations: int) -> str:
        """Calculates the PBKDF2 derived key (used in SCRAM) asynchronously.

            This function offloads the CPU-intensive PBKDF2-HMAC operation to a
            thread pool executor to prevent blocking the asyncio event loop.
            It then encodes the result into a single secure string for storage.

            Args:
                password: The user's plain text password.
                salt: A unique, random byte string for this user.
                iterations: The number of iterations (cost) for the PBKDF2 calculation.

            Returns:
                str: A formatted string containing the algorithm, iterations, salt (in hex),
                     and the resulting hash (in hex), separated by '$' (e.g., "sha256$100000$salt_hex$hash_hex").
                     This format is ideal for securely storing credentials in a single
                     database column.
        """
        function_hashing = partial(
            hashlib.pbkdf2_hmac,
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations
        )

        result = await self._pool.run_in_executor(self._pool_executor, function_hashing)

        salt_hex = binascii.hexlify(salt).decode('ascii')
        hash_hex = binascii.hexlify(result).decode('ascii')

        return f"sha256${iterations}${salt_hex}${hash_hex}"


def SASLFeature(mechanism_list: List[MECHANISM] = None) -> ET.Element:
    """ SASL    Feature Stream message.

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
