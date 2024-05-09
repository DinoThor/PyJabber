import re
from asyncio import Transport
from loguru import logger

from pyjabber.utils import Singleton


class ConectionsManager(metaclass = Singleton):
    __slots__ = ["_peerList", "_autoRegister"]
    
    JID         = "jid"
    TRANSPORT   = "transport"

    def __init__(self, autoRegister = True) -> None:
        self._peerList = {} 
        self._autoRegister = autoRegister

    def get_users_connected(self) -> dict[str, tuple[str, int]]:
        return self._peerList
    
    def get_buffer_by_jid(self, jid) -> Transport | None:
        for key, values in self._peerList.items():
            if re.search(f"{jid}/*", values[self.JID]):
                return self._peerList[key][self.TRANSPORT]
            
        return None

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

    def get_jid(self, peer) -> str | None:
        try:
            return self._peerList[peer][self.JID]
        except KeyError:
            return None

    def set_jid(self, peer, jid, transport = None) -> None | bool:
        try:
            self._peerList[peer][self.JID] = jid
            if transport:
                self._peerList[peer][self.TRANSPORT] = transport
        except KeyError:
            return False

    def autoRegister(self) -> bool:
        return self._autoRegister

