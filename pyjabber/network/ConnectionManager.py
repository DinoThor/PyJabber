import asyncio
import re
from asyncio import Transport
from typing import Dict, Union, Tuple, List
from loguru import logger

from pyjabber.utils import Singleton


class ConnectionManager(metaclass=Singleton):
    __slots__ = ["_peerList", "_remoteList"]

    JID = "jid"
    TRANSPORT = "transport"

    """
    peerList | serverList = {
        "(0.0.0.0, 5000)": {
            "jid"       : <JID>,
            "transport" : <transport>
        },
        ...
    }
    """

    def __init__(self) -> None:
        self._peerList = {}
        self._remoteList = {}

        ###########################################################################

    ############################### LOCAL BOUND ###############################
    ###########################################################################

    def get_users_connected(self) -> Dict[str, Tuple[str, int]]:
        return self._peerList

    def get_buffer_by_jid(self, jid: str) -> List[Tuple[Union[str, Transport]]]:
        # res = []
        # for key, values in self._peerList.items():
        #     if values[self.JID] is None:
        #         continue
        #
        #     if re.match(f"{jid}/*", values[self.JID]):
        #         res.append((self._peerList[key][self.JID], self._peerList[key][self.TRANSPORT]))
        # return res
        halt = 0
        a = [
                (self._peerList[key][self.JID], self._peerList[key][self.TRANSPORT])
                for key, values in self._peerList.items()
                if values[self.JID] is not None and re.match(f"{jid}/*", values[self.JID])
            ]
        return a

    def get_jid_by_peer(self, peer) -> Union[str, None]:
        try:
            return self._peerList[peer][self.JID]
        except KeyError:
            return None

    def set_jid(self, peer, jid, transport=None) -> Union[None, bool]:
        try:
            self._peerList[peer][self.JID] = jid
            if transport:
                self._peerList[peer][self.TRANSPORT] = transport
        except KeyError:
            return False

    def connection(self, peer) -> None:
        if peer not in self._peerList:
            self._peerList[peer] = {
                self.JID: None,
                self.TRANSPORT: None
            }

    def disconnection(self, peer) -> None:
        try:
            self._peerList.pop(peer)
        except KeyError:
            logger.error(f"{peer} not present in the online list")

    ###########################################################################
    ############################# REMOTE SERVER ###############################
    ###########################################################################

    def connectionServer(self, peer) -> None:
        if peer not in self._remoteList:
            self._remoteList[peer] = {
                self.JID: None,
                self.TRANSPORT: None
            }

    def disconnectionServer(self, peer) -> None:
        try:
            self._remoteList.pop(peer)
        except KeyError:
            logger.error(f"{peer} not present in the online list")

    # def check_server_stream_avaliable(self, jid):
    #     try:
    #         return self._remoteList[jid][self.TRANSPORT]
    #     except KeyError:
    #         loop = asyncio.get_running_loop()
    #         a = loop.run_until_complete(self.create_server_connection(loop, jid))
    #         print(a)

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
