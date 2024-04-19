from xml.etree import ElementTree as ET

class Message(ET.Element):
    def __init__(
            self, 
            mto     : str,
            mfrom   : str,
            id      : str,
            body    : str,
            mtype   : str = "chat",
            lang    : str = "en",
            tag     : str = "message", 
            **extra : str) -> None:
        
        attrib: dict[str, str] = {}
        
        attrib["to"]        = mto
        attrib["from"]      = mfrom
        attrib["mtype"]     = mtype
        attrib["id"]        = id
        attrib["xml:lang"]  = lang
        
        super().__init__(tag, attrib, **extra)

        body_elem = ET.Element("body")
        body_elem.text = body

        self.append(body_elem)