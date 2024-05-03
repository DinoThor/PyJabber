from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from pyjabber.features.FeatureInterface import FeatureInterface

class Bind(FeatureInterface):
    pass


class ResourceBinding(Element):
    def __init__(self) -> None:
        super().__init__("bind", {"xmlns" : "urn:ietf:params:xml:ns:xmpp-bind"})
