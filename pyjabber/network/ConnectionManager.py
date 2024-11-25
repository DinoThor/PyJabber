import re
from typing import List
from asyncio import Transport
from typing import Dict, Union, Tuple
from loguru import logger

from pyjabber.stream.JID import JID as JIDClass
from pyjabber.utils import Singleton


peerName = Tuple[str, str]
peerItem = Dict[JIDClass, Transport]
peerList = [peerName, peerItem]


class ConnectionManager(metaclass=Singleton):
    JID = "jid"
    TRANSPORT = "transport"

    def __init__(self, task_s2s=None) -> None:
        if task_s2s:
            self._task_s2s = task_s2s

        self._peerList: peerList = {}
        self._remoteList = {}

    ###########################################################################
    ############################### LOCAL BOUND ###############################
    ###########################################################################

    def get_users_connected(self) -> peerList:
        """
            Return all the users connected

            :return: A dictionary of users connected in the format { (IP, PORT): {jid: <JID>, transport:
            <TRANSPORT> }}
        """
        return self._peerList

    def get_buffer(self, jid: Union[JIDClass]) -> List[Tuple[JIDClass, Transport]]:
        """
            Get all the available buffers associated with a jid.

            If the jid is in the format username@domain/resource, the function
            will only return one buffer or none.

            If the jid is in the format username@domain, the function
            will return a list of the buffers for each resource available.

            :param jid: The jid to get the buffers for. It can be a full jid or a bare jid
            :return: (<JID>, <TRANSPORT>) tuple
        """

        return [(self._peerList[key][self.JID], self._peerList[key][self.TRANSPORT])
                for key, values in self._peerList.items()
                if values[self.JID] is not None and re.match(f"{str(jid)}/*", str(values[self.JID]))
                ]

    def get_jid(self, peer) -> Union[JIDClass, None]:
        """
            Return the jid associated with the peername

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """
        try:
            return self._peerList[peer][self.JID]
        except KeyError:
            return None

    def set_jid(self, peer: Tuple[str, int], jid: JIDClass, transport: Transport = None) -> Union[None, bool]:
        """
            Set/update the jid of a registered connection.

            An optional transport argument can be provided, in order to
            set/update the stored buffer

            :param peer: The peer value in the tuple format ({IP}, {PORT})
            :param jid: The jid to set/update
            :param transport: Transport to use
        """
        try:
            self._peerList[peer][self.JID] = jid
            if transport:
                self._peerList[peer][self.TRANSPORT] = transport
        except KeyError:
            return False

    def connection(self, peer, transport: Transport=None) -> None:
        """
            Store a new connection, without jid or transport.
            Those will be added in the future with the set_jid method.

            :param peer: The peer value in the tuple format ({IP}, {PORT})
            :param transport: The transport object associated to the connection
        """
        if peer not in self._peerList:
            self._peerList[peer] = {
                self.JID: None,
                self.TRANSPORT: transport
            }

    def close(self, peer) -> None:
        """
            Closes a connection by sending a '</stream:stream> message' and
            deletes it from the peers list

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """
        try:
            buffer: Transport = self._peerList.pop(peer)[self.TRANSPORT]
            buffer.write('</stream:stream>'.encode())
            self.disconnection(peer)
        except KeyError as e:
            logger.error(f"{peer} not present in the online list")
            raise e

    def disconnection(self, peer) -> None:
        """
            Remove a stored connection.

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """
        try:
            self._peerList.pop(peer)
        except KeyError:
            logger.error(f"{peer} not present in the online list")

    ###########################################################################
    ############################# REMOTE SERVER ###############################
    ###########################################################################

    def connection_server(self, peer, host, transport) -> None:
        """
            Store a new connection, without jid or transport.
        """
        if peer not in self._remoteList:
            self._remoteList[peer] = {
                self.JID: host,
                self.TRANSPORT: None
            }

    def disconnection_server(self, peer) -> None:
        """
        Remove a present server connection in the list
        i.e. EOF recived, or TCP connection lost
        """
        try:
            self._remoteList.pop(peer)
        except KeyError:
            logger.error(f"{peer} not present in the online list")

    def get_server_buffer(self, host: str) -> Union[Tuple[str, Transport], None]:
        """
            Return the buffer associated with the given host
            :return: (<HOST>, <TRANSPORT>) tuple
        """
        if self.check_server_stream_available(host):
            key = next((k for k, v in self._remoteList.items() if v.get(self.JID) == host), None)
            return self._remoteList[key][self.JID], self._remoteList[key][self.TRANSPORT]

        if self.check_server_present_in_list(host):
            return

        self._task_s2s(host)

    def get_server_host(self, peer: Tuple[str, int]):
        """
            Return the host associated with the given peer.
            :return: Hostname
        """
        try:
            return self._remoteList[peer]["host"]
        except KeyError:
            return None

    def set_server_transport(self, peer: Tuple[str, int], transport: Transport) -> Union[None, bool]:
        """
            Set/update the transport of a registered server connection.

            :param peer: The peer value in the tuple format ({IP}, {PORT})
            :param transport: Transport to use
        """
        try:
            self._remoteList[peer][self.TRANSPORT] = transport
        except KeyError:
            return False

    def set_server_host(self, peer: Tuple[str, int], host: str):
        """
            Set/update the host of a registered server connection.

            :param peer: The peer value in the tuple format ({IP}, {PORT})
            :param host: New host name
        """
        try:
            self._remoteList[peer]["host"] = host
        except KeyError:
            return False

    def check_server_stream_available(self, host) -> bool:
        for k, v in self._remoteList.items():
            if v[self.JID] == host:
                return v[self.TRANSPORT] is not None

    def check_server_present_in_list(self, host) -> bool:
        try:
            if [v for v in self._remoteList.values() if v[self.JID] == host]:
                return True
        except KeyError:
            return False
