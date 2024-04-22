import re
from utils import Singleton
from loguru import logger

class ConectionsManager(metaclass = Singleton):
    __slots__ = [
        "_peerList",
        "_autoRegister"
    ]
    
    JID = "jid"
    TRANSPORT = "transport"

    def __init__(self, autoRegister = True) -> None:
        self._peerList = {} 
        self._autoRegister = autoRegister

    def get_users_connected(self):
        return self._peerList
    
    def get_buffer_by_jid(self, jid):
        for key, values in self._peerList.items():
            if re.search(f"{jid}/*", values[self.JID]):
                return self._peerList[key][self.TRANSPORT]
            
        return None

    def connection(self, peer):
        if peer not in self._peerList:
            self._peerList[peer] = {
                self.JID       : None,
                self.TRANSPORT : None
            } 

    def disconnection(self, peer):
        try:
            self._peerList.pop(peer)
        except KeyError:
            logger.error(f"{peer} not present in the online list")

    def get_jid(self, peer):
        try:
            return self._peerList[peer][self.JID]
        except KeyError:
            pass

    def set_jid(self, peer, jid, transport):
        try:
            self._peerList[peer][self.JID]         = jid
            self._peerList[peer][self.TRANSPORT]   = transport
        except KeyError:
            raise Exception()

    def autoRegister(self):
        return self._autoRegister

