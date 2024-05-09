from xml.etree import ElementTree as ET


class InBandRegistration(ET.Element):
    def __init__(
            self, 
            tag         : str = "register", 
            attrib      : dict[str, str] = {
                "xmlns" : "http://jabber.org/features/iq-register"
            },
            **extra : str) -> None:
        
        super().__init__(tag, attrib, **extra)  

