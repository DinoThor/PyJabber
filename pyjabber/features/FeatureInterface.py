import xml.etree.ElementTree as ET
from abc import ABCMeta, abstractmethod
from typing import Dict


class FeatureInterface(metaclass=ABCMeta):
    @abstractmethod
    def feed(self, element: ET.Element, extra: Dict[str, any] = None):
        pass
