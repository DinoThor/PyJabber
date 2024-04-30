from abc import ABCMeta
from abc import abstractmethod

from enum import Enum
import xml.etree.ElementTree as ET


class Plugin(metaclass = ABCMeta):
    @abstractmethod
    def feed(self, jid:str, element: ET.Element):
        pass