import re
from typing import List
from asyncio import Transport
from typing import Dict, Union, Tuple
from loguru import logger

from pyjabber.utils import Singleton


class ConnectionManager(metaclass=Singleton):
    JID = "jid"
    TRANSPORT = "transport"

    def __init__(self, task_s2s) -> None:
        self._task_s2s = task_s2s

        self._peerList = {}
        self._remoteList = {}

    ###########################################################################
    ############################### LOCAL BOUND ###############################
    ###########################################################################

    def get_users_connected(self) -> Dict[str, Tuple[str, int]]:
        """
            Return all the users connected

            :return: A dictionary of users connected in the format { (IP, PORT): {jid: <JID>, transport:
            <TRANSPORT> }}
        """
        return self._peerList

    def get_buffer(self, jid: str) -> List[Tuple[str, Transport]]:
        """
            Get all the available buffers associated with a jid.

            If the jid is in the format username@domain/resource, the function
            will only return one buffer or none.

            If the jid is in the format username@domain, the function
            will return a list of the buffers for each resource available.

            :param jid: The jid to get the buffers for. It can be a full
            jid or a bare jid
        """

        return [(self._peerList[key][self.JID], self._peerList[key][self.TRANSPORT])
                for key, values in self._peerList.items()
                if values[self.JID] is not None and re.match(f"{jid}/*", values[self.JID])
                ]

    def get_jid(self, peer) -> Union[str, None]:
        """
            Return the jid associated with the peername

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """
        try:
            return self._peerList[peer][self.JID]
        except KeyError:
            return None

    def set_jid(self, peer: Tuple[str, int], jid: str, transport: Transport = None) -> Union[None, bool]:
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

    def connection(self, peer) -> None:
        """
            Store a new connection, without jid or transport.
            Those will be added in the future with the set_jid method.

            :param peer: The peer value in the tuple format ({IP}, {PORT})
        """
        if peer not in self._peerList:
            self._peerList[peer] = {
                self.JID: None,
                self.TRANSPORT: None
            }

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

    def connection_server(self, peer) -> None:
        """
            Store a new connection, without jid or transport.
        """
        if peer not in self._remoteList:
            self._remoteList[peer] = {
                self.JID: None,
                self.TRANSPORT: None
            }

    def disconnection_server(self, peer) -> None:
        try:
            self._remoteList.pop(peer)
        except KeyError:
            logger.error(f"{peer} not present in the online list")

    def get_server_buffer(self, host: str) -> Dict[str, Tuple[str, Transport]]:
        """
            Return the buffer associated with the given host
            :return: An object in the format { (IP, PORT): {host: <HOST>, transport: <TRANSPORT>}}
        """
        if self.check_server_stream_available(host):
            return self._peerList[host][self.TRANSPORT]

        else:
            self._task_s2s()

    def check_server_stream_available(self, host) -> bool:
        return host in [value[self.JID] for value in self._remoteList.values()]

        # try:
        #     return self._remoteList[jid][self.TRANSPORT]
        # except KeyError:
        #     loop = asyncio.get_running_loop()
        #     a = loop.run_until_complete(self.create_server_connection(loop, jid))
        #     print(a)

    # async def create_server_connection(self, loop, jid):
    #     loop = asyncio.get_running_loop()
    #     return await loop.create_connection(
    #             lambda: XMLServerProtocol(
    #                 namespace           = "jabber:server",
    #                 connection_timeout  = 60,
    #             ),
    #             host    = jid,
    #             port    = 5269,
    #         )
