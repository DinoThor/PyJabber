from xml.etree import ElementTree as ET
from pyjabber.features.FeatureInterface import FeatureInterface


class ResourceBinding(ET.Element):
    def __init__(self) -> None:
        super().__init__("bind", {"xmlns" : "urn:ietf:params:xml:ns:xmpp-bind"})
