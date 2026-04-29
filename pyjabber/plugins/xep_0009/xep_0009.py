from xml.etree import ElementTree as ET

from pyjabber.network.ConnectionManager import ConnectionManager
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import ClarkNotation as CN


class RPC:
    __slots__ = ("_connections",)

    def __init__(self):
        self._connections = ConnectionManager()

    async def feed(self, _, element: ET.Element):
        type_iq = element.attrib.get("type")
        if type_iq == "set":
            error = self.validate_set_stanza(element)
            if error:
                return SE.not_acceptable(error)

        elif type_iq == "result":
            error = self.validate_res_stanza(element)
            if error:
                return SE.not_acceptable(error)

        else:
            return SE.invalid_xml()

        to = element.attrib.get("to")
        if not to:
            return SE.invalid_xml()

        buffer = self._connections.get_transport(JID(to))
        for b in buffer:
            b.transport.write(ET.tostring(element))
        return None

    @staticmethod
    def validate_res_stanza(element: ET.Element):
        ns, tag = CN.break_down(element[0].tag)
        if tag != "query" or ns != "jabber:iq:rpc":
            return "Malformed response"

        query = element.findall("{jabber:iq:rpc}query")
        if len(query) > 1:
            return "Only 1 query field is permeated"
        method_res = query[0].findall("{jabber:iq:rpc}methodResponse")
        if len(method_res) > 1:
            return "Only 1 methodResponse field is permeated"
        method_name = method_res[0].find("{jabber:iq:rpc}methodName")
        if len(method_name) > 1:
            return "Only 1 methodName field is permeated"
        method_res[0].find("{jabber:iq:rpc}params")

        return None

    @staticmethod
    def validate_set_stanza(element: ET.Element):
        ns, tag = CN.break_down(element[0].tag)
        if tag != "query" or ns != "jabber:iq:rpc":
            return "Malformed response"

        query = element.findall("{jabber:iq:rpc}query")
        if len(query) > 1:
            return "Only 1 query field is permeated"
        method_call = query[0].findall("{jabber:iq:rpc}methodCall")
        if len(method_call) > 1:
            return "Only 1 methodCall field is permeated"
        method_name = method_call[0].findall("{jabber:iq:rpc}methodName")
        if len(method_name) > 1:
            return "Only 1 methodName field is permeated"
        method_call[0].findall("{jabber:iq:rpc}params")
        return None

    @staticmethod
    def error_response(to_: JID, from_: JID, id_: str, error: str):
        iq_res = IQ(type_=IQ.TYPE.ERROR, to_=str(to_), from_=str(from_), id_=id_)
        iq_res.append(ET.fromstring(SE.not_acceptable(error)))
        return iq_res
