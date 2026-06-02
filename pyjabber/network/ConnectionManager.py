import asyncio
import re
from asyncio import Transport
from ssl import SSLContext
from typing import List, NamedTuple, Optional, Union
from xml.etree.ElementTree import Element

from loguru import logger

from pyjabber.network.utils.TransportProxy import TransportProxy
from pyjabber.stream.JID import JID


class Peer(NamedTuple):
    ip: str
    port: int


class Client(NamedTuple):
    jid: Optional[JID]
    transport: Transport
    online: bool


class Server(NamedTuple):
    host: Optional[str]
    transport: Optional[Transport]

class ConnectionManager:
    """
    A singleton class used as a repository of connections during the protocols'
    lifecycle.

    It keeps track of both client and protocols connections using
    the following data structures:
    """

    _peerList: dict[Peer, Client] = {}
    _remoteList: dict[Peer, Server] = {}
    _remoteIncomingList: dict[Peer, Server] = {}

    _orphan_jids: dict[Peer, JID] = {}
    _orphan_hosts: dict[Peer, str] = {}

    _lock = asyncio.Lock()

    def __init__(self) -> None:
        pass

    ###########################################################################
    ############################## LOCAL BOUND ################################
    ###########################################################################

    async def connection(self, peer: Peer, transport=None) -> None:
        async with self._lock:
            if peer not in self._peerList:
                self._peerList[peer] = Client(None, transport, False)

    async def close(self, peer: Peer) -> None:
        """Closes a connection by sending a '</stream:stream> message' and
        deletes it from the peers list
        """
        try:
            async with self._lock:
                client = self._peerList.pop(peer)
                if client.jid:
                    self._orphan_jids[peer] = client.jid

            client.transport.write("</stream:stream>".encode())
            client.transport.close()
        except KeyError:
            logger.error(f"{peer} not present in the peer list")

    async def online(self, jid: JID):
        if jid.resource is None:
            raise ValueError("JID must have a resource")

        async with self._lock:
            for peer, client in self._peerList.items():
                if client.jid == jid:
                    self._peerList[peer] = self._peerList[peer]._replace(online=True)

    async def offline(self, jid: JID):
        if jid.resource is None:
            raise ValueError("JID must have a resource")

        async with self._lock:
            for peer, client in self._peerList.items():
                if client.jid == jid:
                    self._peerList[peer] = self._peerList[peer]._replace(online=False)

    async def get_transport(self, jid: JID) -> Union[Client, List[Client], None]:
        """Get all the available buffers associated with a JID.

            - If the JID is in the full format <username@domain/resource>, it will only
            return one buffer.
            - If the JID is in the bare format <username@domain>, it will return a list
            of the buffers for each resource available.

        """
        async with self._lock:
            if jid.resource:
                return next((c for c in self._peerList.values() if jid == c.jid), None)
            else:
                return [
                    c
                    for c in self._peerList.values()
                    if re.match(f"{str(jid)}/*", str(c.jid))
                ]

    async def get_transport_online(self, jid: JID) -> List[Client]:
        """Get all the available buffers associated with a JID
        that are ready to receive messages (online).

            - If the JID is in the full format <username@domain/resource>, it will only
            return one buffer (or empty list).
            - If the JID is in the bare format <username@domain>, it will return a list
            of the buffers for each resource available.

        Both cases return a list.
        """
        async with self._lock:
            if jid.resource:
                return [c for c in self._peerList.values() if jid == c.jid and c.online]
            else:
                return [
                    c
                    for c in self._peerList.values()
                    if re.match(f"{str(jid)}/*", str(c.jid)) and c.online
                ]

    async def update_transport_peer(
        self, new_transport: Union[Transport, TransportProxy], peer: Peer
    ):
        async with self._lock:
            try:
                self._peerList[peer] = self._peerList[peer]._replace(
                    transport=new_transport
                )
            except KeyError:
                raise KeyError(
                    "Unable to find client with given peer. Check this inconsistency"
                )

    async def update_transport_jid(
        self, new_transport: Union[Transport, TransportProxy], jid: JID
    ):
        if jid.resource is None:
            raise ValueError("JID must have a resource to update transport")

        async with self._lock:
            match = next(
                (peer for peer, client in self._peerList.items() if client.jid == jid)
                , None
            )
            if match:
                self._peerList[match] = self._peerList[match]._replace(
                    transport=new_transport
                )
            else:
                raise KeyError(
                    "Unable to find client with given JID. Check this inconsistency"
                )

    async def get_jid(self, peer: Peer) -> Union[JID, None]:
        async with self._lock:
            try:
                return self._peerList[peer].jid
            except KeyError:
                self._orphan_jids.pop(peer, None)

    async def set_jid(
        self, peer: Peer, jid: JID, transport: Union[Transport, None] = None
    ) -> None:
        """Set/update the jid of a registered connection.

        An optional transport argument can be provided, in order to set/update
        the stored buffer
        """
        async with self._lock:
            try:
                self._peerList[peer] = self._peerList[peer]._replace(
                    jid=jid,
                    transport=transport if transport else self._peerList[peer].transport,
                )
            except KeyError:
                raise KeyError(f"Unable to find {peer} during jid/transport update")

    async def update_resource(self, peer: Peer, resource: str):
        async with self._lock:
            try:
                self._peerList[peer].jid.resource = resource
            except KeyError:
                raise KeyError(f"Unable to find {peer} during resource update")

    ###########################################################################
    ############################# REMOTE SERVER ###############################
    ###########################################################################

    async def connection_server(
        self,
        peer: Peer,
        transport: Union[Transport, None] = None,
        host: Union[str, None] = None
    ) -> None:
        async with self._lock:
            if peer not in self._remoteList:
                self._remoteList[peer] = Server(host, transport)

    async def close_server(self, peer: Peer) -> None:
        """Closes a connection by sending a '</stream:stream> message' and
        deletes it from the remote list
        """
        async with self._lock:
            try:
                client = self._remoteList.pop(peer)
                client.transport.write("</stream:stream>".encode())
                if client.host:
                    self._orphan_hosts[peer] = client.host
            except KeyError:
                logger.error(f"{peer} not present in the remote list")

    async def get_host(self, peer: Peer) -> Union[str, None]:
        async with self._lock:
            try:
                return self._remoteList[peer].host
            except KeyError:
                return self._orphan_hosts.pop(peer, None)

    async def set_host(self, peer: Peer, host: str, transport: Transport = None) -> None:
        """Set/update the host of a registered server connection.

        An optional transport argument can be provided, in order to set/update
        the stored buffer
        """
        async with self._lock:
            try:
                self._remoteList[peer] = self._remoteList[peer]._replace(
                    host=host,
                    transport=transport if transport else self._remoteList[peer].transport,
                )
            except KeyError:
                raise KeyError(f"Unable to find {peer} during host/transport update")

    async def update_host(self, peer: Peer, host: str) -> None:
        async with self._lock:
            try:
                self._remoteList[peer] = self._remoteList[peer]._replace(host=host)
            except KeyError:
                logger.warning(
                    "Unable to find protocols with given peer during host update. "
                    "Check this inconsistency"
                )

    async def get_server_transport_peer(self, peer: Peer) -> Union[Transport, None]:
        async with self._lock:
            try:
                return self._remoteList.get(peer).transport
            except KeyError:
                return None

    async def get_server_transport_host(self, host: str) -> Union[Transport, None]:
        async with self._lock:
            return next(
                (s.transport for s in self._remoteList.values() if s.host == host), None
            )

    async def update_transport_server(self, new_transport: Transport, peer: Peer):
        async with self._lock:
            try:
                self._remoteList[peer] = self._remoteList[peer]._replace(
                    transport=new_transport
                )
            except KeyError:
                logger.warning(
                    "Unable to find protocols with given peer. Check this inconsistency"
                )

    async def get_server_host(self, peer: Peer) -> Union[str, None]:
        async with self._lock:
            try:
                return self._remoteList.get(peer).host
            except KeyError:
                return None

    async def set_host_server(self, peer: Peer, host: str):
        async with self._lock:
            try:
                self._remoteList[peer] = self._remoteList[peer]._replace(host=host)
            except KeyError:
                raise KeyError(f"Unable to find {peer} during host update")

    async def get_connection_ssl_certificate(
        self, peer: Peer
    ) -> Union[SSLContext, None]:
        async with self._lock:
            try:
                self._remoteList.get(peer).transport.get_extra_info("ssl_object")
            except KeyError:
                return None

    ###########################################################################
    ############################# REMOTE SERVER ###############################
    ###########################################################################

    async def connection_server_incoming(
        self, peer: Peer, transport: Transport = None, host: str = None
    ) -> None:
        async with self._lock:
            if peer not in self._remoteIncomingList:
                self._remoteIncomingList[peer] = Server(host, transport)

    async def close_server_incoming(self, peer: Peer) -> None:
        """Closes a connection by sending a '</stream:stream> message' and
        deletes it from the remote incoming list
        """
        async with self._lock:
            try:
                client = self._remoteIncomingList.pop(peer)
                client.transport.write("</stream:stream>".encode())

                if client.host:
                    await self._presence.put(
                        (client.host, Element("presence", attrib={"type": "INTERNAL"}))
                    )

                client.transport.close()
            except KeyError:
                logger.error(f"{peer} not present in the remote incoming list")
