import xml.etree.ElementTree as ET
from typing import Dict


class Presence(ET.Element):
    def __init__(
            self,
            tag: str = "presence",
            attrib: Dict[str, str] = ...,
            **extra: str) -> None:
        super().__init__(tag, attrib, **extra)
