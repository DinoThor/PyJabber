import re
from asyncio import Transport
from typing import Union
from loguru import logger

from pyjabber.utils import Singleton


class ConectionManager(metaclass = Singleton):
    __slots__ = ["_peerList"]
    
    JID         = "jid"
    TRANSPORT   = "transport"

    def __init__(self) -> None:
        self._peerList = {} 

    def get_users_connected(self) -> dict[str, tuple[str, int]]:
        return self._peerList
    
    def get_buffer_by_jid(self, jid: str) -> tuple[str | Transport]:
        res = []
        for key, values in self._peerList.items():
            if values[self.JID] is None:
                continue

            if re.match(f"{jid}/*", values[self.JID]):
                res.append((self._peerList[key][self.JID], self._peerList[key][self.TRANSPORT]))            
        
        return res
    
    def get_jid_by_peer(self, peer) -> Union[str, None]:
        try:
            return self._peerList[peer][self.JID]
        except KeyError:
            return None
        
    def set_jid(self, peer, jid, transport = None) -> Union[None, bool]:
        try:
            self._peerList[peer][self.JID] = jid
            if transport:
                self._peerList[peer][self.TRANSPORT] = transport
        except KeyError:
            return False

    def connection(self, peer) -> None:
        if peer not in self._peerList:
            self._peerList[peer] = {
                self.JID       : None,
                self.TRANSPORT : None
            } 

    def disconnection(self, peer) -> None:
        try:
            self._peerList.pop(peer)
        except KeyError:
            logger.error(f"{peer} not present in the online list")
