import os
import xml.etree.ElementTree as ET

from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.network.ConnectionManager import ConnectionManager

FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class StanzaServerOutcomingHandler:
    def __init__(self, buffer) -> None:
        self._buffer = buffer
        self._connection_manager = ConnectionManager()
        self._peername = buffer.get_extra_info('peername')
        self._host = self._connection_manager.get_server_host(self._peername)

        self._functions = {
            "{jabber:client}iq": self.handle_iq,
            "{jabber:client}message": self.handle_msg,
            "{jabber:client}presence": self.handle_pre
        }

    def feed(self, element: ET.Element):
        try:
            self._functions[element.tag](element)
        except KeyError:
            self._buffer.write(SE.bad_request())

    ############################################################
    ############################################################

    def handle_iq(self, element: ET.Element):
        return

    def handle_msg(self, element: ET.Element):
        bare_jid = element.attrib["to"].strip("/")[0]

        receiver_buffer = self._connection_manager.get_buffer(bare_jid)

        for buffer in receiver_buffer:
            buffer[1].write(ET.tostring(element))

    def handle_pre(self, element: ET.Element):
        return
