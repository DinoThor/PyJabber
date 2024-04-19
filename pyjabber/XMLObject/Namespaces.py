import enum

class Namespaces(enum.Enum):
    '''
    Defines the available namespaces in the protocol.
    '''
    XMLSTREAM   = "http://etherx.jabber.org/streams"
    CLIENT      = "jabber:client"
    SERVER      = "jabber:server"

    STARTTLS    = "urn:ietf:params:xml:ns:xmpp-tls"
    SASL        = "urn:ietf:params:xml:ns:xmpp-sasl"
    BIND        = "urn:ietf:params:xml:ns:xmpp-bind"