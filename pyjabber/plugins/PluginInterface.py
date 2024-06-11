from abc import ABC
from abc import abstractmethod

import xml.etree.ElementTree as ET


class Plugin(ABC):
    @abstractmethod
    def __init__(self, jid: str):
        self.jid = jid

    @abstractmethod
    def feed(self, element: ET.Element):
        pass
