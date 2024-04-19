import xml.etree.ElementTree as ET

class IQ(ET.Element):
    def __init__(
            self, 
            tag: str, 
            attrib: dict[str, str] = ..., 
            **extra: str) -> None:
        
        super().__init__(tag, attrib, **extra)

        self._handler = {
            "get"       : self.handle_get,
            "result"    : self.handle_result,
            "set"       : self.handle_set,
            "error"     : self.handle_error
        
        }

    def feed(self, element: ET.Element):
        self._handler[element.attrib["type"]](element)

    def handle_get(self, element):
        xmlns = element.find('jabber:iq:roster#query')

    def handle_set(self, element):
        pass

    def handle_result(self, element):
        pass

    def handle_error(self, element):
        pass

    def query():
        pass
