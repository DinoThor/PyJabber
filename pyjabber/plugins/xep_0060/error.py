from enum import Enum
from xml.etree import ElementTree as ET

from pyjabber import metadata
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID


class ErrorType(Enum):
    INVALID_JID = "<error type='modify'><bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><invalid-jid xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    CONFLICT = "<error type='auth'><conflict xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
    NOT_ACCEPTABLE = "<error type='auth'><not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><nodeid-required xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    ITEM_NOT_FOUND = "<error type='cancel'><item-not-found xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
    FORBIDDEN = "<error type='auth'><forbidden xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
    PENDING_SUBSCRIPTION = "<error type='auth'><not-authorized xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><pending-subscription xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    SUBID_REQUIRED = "<error type='modify'><bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><subid-required xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    NODEID_REQUIRED = "<error type='modify'><bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><nodeid-required xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    ITEM_REQUIRED = "<error type='modify'><bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><item-required xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    INVALID_SUBID = "<error type='modify'><not-acceptable xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><invalid-subid xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    NOT_SUBSCRIBED = "<error type='cancel'><unexpected-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><not-subscribed xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    NODE_FULL = "<error type='cancel'><conflict xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><node-full xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"
    INVALID_PAYLOAD = "<error type='modify'><bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><invalid-payload xmlns='http://jabber.org/protocol/pubsub#errors'/></error>"


def error_response(element: ET.Element, jid: JID, error: ErrorType):
    iq_res = IQ(type_=IQ.TYPE.ERROR, from_=metadata.HOST, to=str(jid), id_=element.attrib.get('id'))
    auth_error = ET.fromstring(error.value)
    iq_res.append(auth_error)
    return ET.tostring(iq_res)
