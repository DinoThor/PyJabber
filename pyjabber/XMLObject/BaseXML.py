from typing_extensions import override
from xml.etree import ElementTree

class BaseXML(ElementTree.Element):
    '''
    Base class for all the xml elements. 
    Inherits from xml.etree.ElementTree.Element.
    '''
    def __init__(
            self, 
            tag, 
            attrib = {}, 
            **extra):
        super().__init__(tag, attrib) 

    @override
    def fromstring(self, xml_string) ->  None:
        '''
        Parse a string to an xml element.
        '''
        element     = ElementTree.fromstring(xml_string)
        self.tag    = element.tag
        self.text   = element.text
        self.tail   = element.tail
        self.attrib = element.attrib   

    @override
    def tostring(self) -> str:
        '''
        Convert the xml element to a string.
        '''
        return ElementTree.tostring(self, encoding="utf-8", method="xml")
    
    def open_tag(self) -> bytes:
        '''
        Return the open tag of the element.
        '''
        tag = '<' + self.tag + ' '
        for a in self.attrib:
            tag += a + '="' + self.attrib[a] + '" '
        tag += '>'
        return tag.encode()
    
    def close_tag(self) -> bytes:
        '''
        Return the close tag of the element.
        '''
        return '</' + self.tag + '>'.encode()