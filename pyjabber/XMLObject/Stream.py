from uuid import uuid4
from XMLObject import BaseXML
from XMLObject.Namespaces import Namespaces

class Stream(BaseXML):
    '''
    Stream open tag to open a stream connection.
    '''
    def __init__(
            self, 
            id          = None, 
            from_       = None, 
            to          = None, 
            version     = (1, 0), 
            xml_lang    = "en", 
            xmlns       = "a"):
        super().__init__(tag = "stream:stream")

        self.id         = id
        self.from_      = from_
        self.to         = to
        self.version    = str(version[0]) + "." + str(version[1])
        self.xml_lang   = xml_lang
        self.xmlns      = xmlns

        self.set("xmlns:stream", Namespaces.XMLSTREAM.value)


    @property
    def id(self):
        return self.get("id")
    
    @id.setter
    def id(self, value):
        if value:
            self.set("id", value)
        else:
            for id in self.findall("id"): self.remove(id)

    @property
    def from_(self):
        return self.get("from")
    
    @from_.setter
    def from_(self, value):
        if value:
            self.set("from", value)
        else:
            for from_ in self.findall("from"): self.remove(from_)

    @property
    def to(self):
        return self.get("to")
    
    @to.setter
    def to(self, value):
        if value:
            self.set("to", value)
        else:
            for to in self.findall("to"): self.remove(to)

    @property
    def version(self):
        return self.get("version")
    
    @version.setter
    def version(self, value):
        if value:
            self.set("version", value)
        else:
            for version in self.findall("version"): self.remove(version)

    @property
    def xml_lang(self):
        return self.get("xml:lang")
    
    @xml_lang.setter
    def xml_lang(self, value):
        if value:
            self.set("xml:lang", value)
        else:
            for xml_lang in self.findall("xml:lang"): self.remove(xml_lang)

    @property
    def xmlns(self):
        return self.get("xmlns")
    
    @xmlns.setter
    def xmlns(self, value):
        if value:
            self.set("xmlns", value)
        else:
            for xmlns in self.findall("xmlns"): self.remove(xmlns)

    @property
    def xmlns_stream(self):
        return self.get("xmlns:stream")
    

def responseStream(attrs):
    # Load attributes
    attrs = dict(attrs)

    # Get attributes
    id_     = str(uuid4())
    from_   = attrs.pop((None, "from"), None)
    to      = attrs.pop((None, "to"), None)
    version = tuple(map(int, attrs.pop((None, "version"), "0.9").split(".")))
    lang    = attrs.pop(("http://www.w3.org/XML/1998/namespace", "lang"), None)

    # Create response attributes
    return Stream(
        id          = id_,
        from_       = to,
        to          = from_,
        version     = version,
        xml_lang    = lang,
        xmlns       = Namespaces.CLIENT.value
    )

def recivedStream(attrs):
    attrs = dict(attrs)

    from_   = attrs.pop((None, "from"), None)
    to      = attrs.pop((None, "to"), None)
    version = tuple(map(int, attrs.pop((None, "version"), "0.9").split(".")))
    lang    = attrs.pop(("http://www.w3.org/XML/1998/namespace", "lang"), None)

    return Stream(
        from_       = from_,
        to          = to,
        version     = version,
        xml_lang    = lang,
        xmlns       = Namespaces.CLIENT.value
    )
