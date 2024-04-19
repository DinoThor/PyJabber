import re
from utils import Singleton
from loguru import logger

class ConectionsManager(metaclass = Singleton):
    __slots__ = [
        "_peerList",
        "_autoRegister"
    ]
    
    def __init__(self, autoRegister = True) -> None:
        self._peerList = {} 
        self._autoRegister = autoRegister

    def get_users_connected(self):
        return self._peerList
    
    def get_buffer_by_jid(self, jid):
        for key, values in self._peerList.items():
            if re.search(f"{jid}/*", values["jid"]):
                return self._peerList[key]["transport"]
            
        return None

    def connection(self, peer):
        if peer not in self._peerList:
            self._peerList[peer] = {
                "jid"       : None,
                "transport" : None
            } 

    def setJID(self, peer, jid, transport):
        try:
            self._peerList[peer]["jid"]         = jid
            self._peerList[peer]["transport"]   = transport
        except KeyError:
            raise Exception()

    def disconnection(self, peer):
        try:
            self._peerList.pop(peer)
        except KeyError:
            logger.error(f"{peer} not present in the online list")

    def autoRegister(self):
        return self._autoRegister

