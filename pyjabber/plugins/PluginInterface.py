import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod


class Plugin(ABC):
    @abstractmethod
    def __init__(self, jid: str):
        self.jid = jid

    @abstractmethod
    def feed(self, element: ET.Element):
        pass
