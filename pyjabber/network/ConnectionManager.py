import asyncio
import re
from typing import List, Optional
from asyncio import Transport
from typing import Dict, Union, Tuple
from loguru import logger

from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton

PeerList = Dict[
    Tuple[str, int],
    Tuple[Optional[JID], Transport, List[bool]]
]


# EXAMPLE
# peerList = {
#     ("0.0.0.0", "50000"): (<JID(demo@localhost/12341234)>, <asyncio.Transport>, <Online: Bool>),
#     ("0.0.0.0", "50001"): (<JID(test@localhos/43214321)>, <asyncio.Transport>, <Online: Bool>)
# }
#
# remoteList = {
#   ("0.0.0.0", "50000"): ("domain.es", <asyncio.Transport>),
#   ("0.0.0.0", "50001"): ("host.com", <asyncio.Transport>)
# }
#
#



class ConnectionManager(metaclass=Singleton):
    def __init__(self) -> None:

        self._peerList: PeerList = {}
        self._remoteList = {}

    ###########################################################################
    ############################## LOCAL BOUND ################################
    ###########################################################################

    def connection(self, peer: Tuple[str, int], transport: Transport = None) -> None:
        """
            Store a new connection, without jid or transport.
            Those will be added in the future with the set_jid method.

            :param peer: The peer value in the tuple format ({IP}, {PORT})
            :param transport: The transport object associated to the connection
        """
        if peer not in self._peerList:
            self._peerList[peer] = (None, transport, [False])

    def disconnection(self, peer: Tuple[str, int]) -> None:
        """
            Remove a stored connection

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """

        try:
            self._peerList.pop(peer)
        except KeyError:
            logger.warning(f"{peer} not present in the online list")

    def online(self, jid: JID, online: bool = True):
        for k, v in self._peerList.items():
            if v[0] == jid and v[2][0] != online:
                self._peerList[k] = (v[0], v[1], [online])

    def close(self, peer: Tuple[str, int]) -> None:
        """
            Closes a connection by sending a '</stream:stream> message' and
            deletes it from the peers list

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """
        try:
            _, buffer, _ = self._peerList.pop(peer)
            buffer.write('</stream:stream>'.encode())
            self.disconnection(peer)
        except KeyError as e:
            logger.error(f"{peer} not present in the online list")

    def get_users_connected(self) -> PeerList:
        """
            Return all the users connected

            :return: peerList
        """
        return self._peerList

    def get_buffer(self, jid: JID) -> List[Tuple[JID, Transport, bool]]:
        """
            Get all the available buffers associated with a jid.

            If the jid is in the format username@domain/resource, the function
            will only return one buffer or none.

            If the jid is in the format username@domain, the fun<Online: Bool>ction
            will return a list of the buffers for each resource available.

            Both cases return a list.

            :param jid: The jid to get the buffers for. It can be a full jid or a bare jid
            :return: (JID, TRANSPORT) tuple
        """
        if jid.resource:
            return [(jid_stored, buffer, online[0])
                    for jid_stored, buffer, online in self._peerList.values()
                    if jid == jid_stored]
        else:
            return [(jid_stored, buffer, online[0])
                    for jid_stored, buffer, online in self._peerList.values()
                    if re.match(f"{str(jid)}/*", str(jid_stored))]

    def get_buffer_online(self, jid: JID) -> List[Tuple[JID, Transport, bool]]:
        """
            Get all the available buffers associated with a jid
            that are ready to receive messages (online).

            - If the jid is in the format username@domain/resource, the function will only return one buffer or none.

            - If the jid is in the format username@domain, the function will return a list of the buffers for each resource available.

            Both cases return a list.

            :param jid: The jid to get the buffers for. It can be a full jid or a bare jid
            :return: (JID, TRANSPORT) tuple
        """
        if jid.resource:
            return [(jid_stored, buffer, online[0])
                    for jid_stored, buffer, online in self._peerList.values()
                    if jid == jid_stored and online[0] is True]
        else:
            return [(jid_stored, buffer, online[0])
                    for jid_stored, buffer, online in self._peerList.values()
                    if re.match(f"{str(jid)}/*", str(jid_stored))
                    and online[0] is True]

    def update_buffer(self, new_transport: Transport, peer: Tuple[str, int] = None, jid: JID = None):
        if not peer and not jid:
            logger.warning("Missing peer OR jid parameter to update transport in client connection. No action will be performed")
            return

        if peer:
            try:
                jid, old_transport, online = self._peerList[peer]
                self._peerList[peer] = (jid, new_transport, online)
                return
            except KeyError:
                logger.warning("Unable to find client with given peer. Check this inconsistency")
                return

        if jid.resource is None:
            logger.warning("JID must have a resource to update transport")
            return

        match = next(((k, v) for k, v in self._peerList.items() if v[0] == jid), None)
        if match:
            jid, _, online = match[1]
            self._peerList[match[0]] = (jid, new_transport, online)
        else:
            logger.warning("Unable to find client with given JID. Check this inconsistency")



    ###########
    ### JID ###
    ###########

    def get_jid(self, peer: Tuple[str, int]) -> Union[JID, None]:
        """
            Return the jid associated with the peername

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """
        try:
            return self._peerList[peer][0]
        except KeyError:
            return None

    def set_jid(self, peer: Tuple[str, int], jid: JID, transport: Transport = None) -> None:
        """
            Set/update the jid of a registered connection.

            An optional transport argument can be provided, in order to
            set/update the stored buffer

            :param peer: The peer value in the tuple format ({IP}, {PORT})
            :param jid: The jid to set/update
            :param transport: Transport to use
        """
        try:
            _, old_transport, online = self._peerList[peer]
            self._peerList[peer] = (jid, transport or old_transport, online)
        except KeyError:
            logger.error(f"Unable to find {peer} during jid/transport update")

    def update_resource(self, peer: Tuple[str, int], resource: str):
        try:
            self._peerList[peer][0].resource = resource
        except KeyError:
            logger.error(f"Unable to find {peer} during resource update")

    ###########################################################################
    ############################# REMOTE SERVER ###############################
    ###########################################################################
    def connection_server(self, peer: Tuple[str, int], transport: Transport = None, host: str = None) -> None:
        """
            Store a new server connection.

            :param peer: The peer value in the tuple format ({IP}, {PORT})
            :param transport: The transport object associated to the connection
        """
        if peer not in self._remoteList:
            self._remoteList[peer] = (host, transport)

    def disconnection_server(self, peer: Tuple[str, int]) -> None:
        """
            Remove a stored connection, and fires the DisconnectEvent

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """

        try:
            self._remoteList.pop(peer)
        except KeyError:
            logger.warning(f"Server {peer} not present in the online list")

    def update_host(self, peer: Tuple[str, int], host: str) -> None:
        if not peer:
            logger.warning("Need peer to update host on server connection")
            return

        try:
            _, transport = self._remoteList[peer]
            self._remoteList[peer] = (host, transport)
            return
        except KeyError:
            logger.warning("Unable to find server with given peer during host update. Check this inconsistency")
            return

    def close_server(self, peer: Tuple[str, int]) -> None:
        """
            Closes a connection by sending a '</stream:stream> message' and
            deletes it from the remote list

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """
        try:
            _, buffer = self._remoteList.pop(peer)
            buffer.write('</stream:stream>'.encode())
            self.disconnection(peer)
        except KeyError as e:
            logger.error(f"{peer} not present in the online list")

    def get_server_buffer(self, peer: Optional[Tuple[str, str]] = None, host: Optional[str] = None) -> Union[Transport, None]:
        """
            Return the buffer associated with the given host
            :return: (<HOST>, <TRANSPORT>) tuple
        """
        if peer:
            return self._remoteList.get(peer)

        if host:
            try:
                return [buffer for buffer in self._remoteList.values() if buffer[0] == host].pop()
            except IndexError:
                pass

        return None

    def update_transport_server(self, new_transport: Transport, peer: Tuple[str, int] = None, host: str = None):
        if not peer and not host:
            logger.warning("Missing peer OR jid parameter to update transport in server connection. No action will be performed")
            return

        if peer:
            try:
                host, _ = self._remoteList[peer]
                self._remoteList[peer] = (host, new_transport)
                return
            except KeyError:
                logger.warning("Unable to find server with given peer. Check this inconsistency")
                return

        match = next(((k, v) for k, v in self._remoteList.items() if v[0] == host), None)
        if match:
            host, _ = match[1]
            self._remoteList[match[0]] = (host, new_transport)
        else:
            logger.warning("Unable to find server with given host. Check this inconsistency")

    def get_server_host(self, peer: Tuple[str, int]):
        """
            Return the host associated with the given peer.
            :return: Hostname
        """
        return self._remoteList.get(peer)[0] if self._remoteList.get(peer) else None

    def set_host_server(self, peer: Tuple[str, int], host: str):
        entry = self._peerList.get(peer)
        if entry:
            self._remoteList[peer] = (host, entry[1])
