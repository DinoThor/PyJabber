import asyncio
import base64
import binascii
import hashlib
import hmac
from typing import Union
from uuid import uuid4
from xml.etree import ElementTree as ET

import bcrypt
from loguru import logger
from sqlalchemy import insert, select

from pyjabber import metadata
from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.features.SASL.Mechanism import MECHANISM
from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.stream.Stage import Stage
from pyjabber.utils import ClarkNotation as CN
from pyjabber.utils.Exceptions import BadRequestException, InternalServerError


class SASL:
    """
        SASL Class.

        An instance of this class will manage the authentication from new connections,
        during the stream negotiation process.
    """
    def __init__(self, transport, parser, peer, from_claim = None):
        self._handlers = {
            "iq": self.handle_IQ,
            "auth": self.handle_auth
        }
        self._connection_manager = ConnectionManager()
        self._peer = peer

        self._from_claim = from_claim

        self._transport = transport
        self._parser = parser

        self._loop = asyncio.get_running_loop()

        self._semaphore = metadata.SEMAPHORE
        self._pool_executor = metadata.PROCESS_POOL_EXE

    async def feed(self, element: ET.Element) -> Union[Stage, None]:
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

    async def handle_IQ(self, element: ET.Element) -> None:
        query = element.find("{jabber:iq:register}query")
        if query is None:
            raise BadRequestException()

        if element.attrib.get("type") == IQ.TYPE.SET.value:
            new_jid = query.find("{jabber:iq:register}username")
            if new_jid is None:
                raise BadRequestException()

            new_jid = new_jid.text

            async with await DB.connection_async() as con:
                query_db = select(Model.Credentials).where(
                    Model.Credentials.c.jid == new_jid
                )
                credentials = await con.execute(query_db)
                credentials = credentials.fetchone()

            if credentials:
                self._transport.write(
                    SE.conflict_error(element.attrib.get("id"))
                )
            else:
                pwd = query.find("{jabber:iq:register}password").text
                await self._store_hash_task(pwd, new_jid)
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

    async def handle_auth(self, element: ET.Element) -> Union[Stage, None]:
        mechanism = element.attrib.get("mechanism")

        if mechanism == MECHANISM.EXTERNAL.value:
            if not self._from_claim:
                raise BadRequestException()

            cert = self._connection_manager.get_connection_certificate_server(self._peer)
            if not cert:
                logger.error(f"Error retrieving TLS cert from {self._peer}. Closing connection for server safety")
                raise InternalServerError()

            if not self.validate_cert(self._from_claim, cert):
                logger.error(f"Host claim cannot be verified with presented cert. Verify host used on stream or cert: {self._peer}")
                raise InternalServerError()

            self._transport.write(b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
            self._parser.reset_stack()

        try:
            data = base64.b64decode(element.text).split("\x00".encode())
            jid = data[1].decode()
            pwd = data[2].decode()

            async with await DB.connection_async() as con:
                query = select(Model.Credentials.c.hash_pwd).where(Model.Credentials.c.jid == jid)
                hashed_pwd = await con.execute(query)
                hashed_pwd = hashed_pwd.fetchone()

            if not hashed_pwd:
                self._transport.write(SE.not_authorized_sasl())
                self._connection_manager.close(self._peer)

            authorized = await self._verify_password_async(
                stored_password=hashed_pwd[0],
                provided_password=pwd
            )
            if authorized:
                self._connection_manager.set_jid(self._peer, JID(user=jid, domain=metadata.HOST))
                self._transport.write(b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
                self._parser.reset_stack()
                self._transport.resume_reading()
                return Stage.AUTH
            else:
                self._transport.write(SE.not_authorized_sasl())
                self._connection_manager.close(self._peer)

        except Exception as e:
            logger.error(f"Exception during auth process for {element.attrib.get('from')}: {e}")
            self._transport.write(SE.not_authorized_sasl())

    ###############################################################################################

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

    async def _store_hash_task(self, password: str, jid_str: str):
        """Handles the full user registration process by hashing the password and storing credentials.

            This coroutine executes the CPU-intensive password hashing and the I/O-bound
            database insertion, ensuring neither operation blocks the main event loop.
            It concludes the registration by sending an XMPP success response to the client.

            Args:
                password: The user's plain text password to be hashed and stored.
                jid_str: The JID of the user being registered.
        """
        hashed_pwd = await self._hash_scram_async(
            password=password,
            iterations=100000,
            salt=bcrypt.gensalt(rounds=8) if metadata.DATABASE_IN_MEMORY else bcrypt.gensalt()
        )

        async with await DB.connection_async() as con:
            async with con.begin():
                query_insert = insert(Model.Credentials).values({"jid": jid_str, "hash_pwd": hashed_pwd})
                await con.execute(query_insert)

    async def _verify_password_async(self, stored_password: str, provided_password: str) -> bool:
        """
        Verifies a password against the stored string.

        Args:
            stored_password: The full string from the database (e.g., "sha256$100000$salt_hex$hash_hex").
            provided_password: The password entered by the user.

        Returns:
            bool: True if the passwords match, False otherwise.
        """
        try:
            _, iter_str, salt_hex, hash_hex = stored_password.split('$')

            iterations = int(iter_str)
            salt = binascii.unhexlify(salt_hex)

            new_hash = await self._hash_scram_async(provided_password, salt, iterations)
            _, _, _, new_hash = new_hash.split("$")

            return hmac.compare_digest(new_hash, hash_hex)

        except (ValueError, IndexError, binascii.Error):
            return False

    async def _hash_scram_async(self, password: str, salt: bytes, iterations: int) -> str:
        """Calculates the PBKDF2 derived key (used in SCRAM) asynchronously.
            This function offloads the CPU-intensive PBKDF2-HMAC operation to a
            process pool executor to prevent blocking the asyncio event loop.
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
        hashed_pwd = None
        async with self._semaphore:
            hashed_pwd = await self._loop.run_in_executor(
                self._pool_executor,
                hashlib.pbkdf2_hmac,
                'sha256',
                password.encode(),
                salt,
                iterations
            )

        salt_hex = binascii.hexlify(salt).decode('ascii')
        hash_hex = binascii.hexlify(hashed_pwd).decode('ascii')

        return f"sha256${iterations}${salt_hex}${hash_hex}"
