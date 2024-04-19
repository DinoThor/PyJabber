import os.path
import pickle
from uuid import uuid4

from utils import Singleton

PICKLE_PATH = os.getcwd() + "/network/roaster/roasterList.pkl"

class Roaster(metaclass = Singleton):
    
    __slots__ = [
        "_roasterList"
    ]

    def __init__(self) -> None:
        self._roasterList: dict[str, list[str]] = {}
        
        if os.path.isfile(PICKLE_PATH):
            with open(PICKLE_PATH, 'rb') as pkl:
                self._roasterList = pickle.load(pkl)
        else:
            with open(PICKLE_PATH, 'wb') as pkl:
                pickle.dump(self._roasterList, pkl, protocol=pickle.HIGHEST_PROTOCOL)

    def getRoaster(self, id: str = None) -> list[str] | dict[str, list[str]]:
        if id:
            return self._roasterList[id]
        else:
            return self._roasterList
        
    def setRoaster(self, id: str, roaster: list[str]):
        self._roasterList[id] = roaster
        self.backup()

    def addContact(self, id: str, contact: list[str]):
        self._roasterList[id].extend(contact)
        self.backup()

    def backup(self):
        with open(PICKLE_PATH, 'wb') as pkl:
                pickle.dump(self._roasterList, pkl, protocol=pickle.HIGHEST_PROTOCOL)