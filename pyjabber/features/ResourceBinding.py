from xml.etree import ElementTree as ET


class ResourceBinding(ET.Element):
    def __init__(self) -> None:
        super().__init__("bind", {"xmlns": "urn:ietf:params:xml:ns:xmpp-bind"})
