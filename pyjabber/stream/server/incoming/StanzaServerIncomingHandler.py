import os
import pickle
import xml.etree.ElementTree as ET
import xmlschema

from pyjabber.features.presence.PresenceFeature import Presence
from pyjabber.stanzas.error import StanzaError as SE

FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class StanzaServerHandler:
    def __init__(self, buffer, connection_manager) -> None:
        self._buffer = buffer
        self._connection_manager = connection_manager
        self._peername = buffer.get_extra_info('peername')
        self._host = self._connection_manager.get_server_host(self._peername)
        self._presenceManager = Presence(self._host)

        self._functions = {
            "{jabber:client}iq": self.handle_iq,
            "{jabber:client}message": self.handle_msg,
            "{jabber:client}presence": self.handle_pre
        }

        with open(os.path.join(FILE_PATH, "..", "..", "schemas", "schemas.pkl"), "rb") as schemasDump:
            self._schemas = pickle.load(schemasDump)

    def feed(self, element: ET.Element):
        try:
            schema: xmlschema.XMLSchema = self._schemas[CN.deglose(element.tag)[
                0]]
            if schema.is_valid(ET.tostring(element)) is False:
                self._buffer.write(SE.bad_request())
        except KeyError:
            self._buffer.write(SE.feature_not_implemented())

        try:
            self._functions[element.tag](element)
        except KeyError:
            self._buffer.write(SE.bad_request())

    ############################################################
    ############################################################

    def handle_iq(self, element: ET.Element):
        return

    def handle_msg(self, element: ET.Element):
        receiver_buffer = self._connection_manager.get_buffer(element.attrib["to"])

        for buffer in receiver_buffer:
            buffer[-1].write(ET.tostring(element))

    def handle_pre(self, element: ET.Element):
        res = self._presenceManager.feed(element, self._jid)
        if res:
            self._buffer.write(res)
