import xml.etree.ElementTree as ET

from abc import ABCMeta
from abc import abstractmethod


class FeatureInterface(metaclass = ABCMeta):
    @abstractmethod
    def feed(element: ET.Element, extra: dict[str, any] = None):
        pass