import xml.etree.ElementTree as ET

class Presence(ET.Element):
    def __init__(
            self, 
            tag: str = "presence", 
            attrib: dict[str, str] = ..., 
            **extra: str) -> None:
        super().__init__(tag, attrib, **extra)