# from asyncio import BaseProtocol
# from enum import Enum
# from loguru import logger
# from xml.sax import ContentHandler
# from xml.etree import ElementTree as ET
#
# from pyjabber.stream import Stream
# from pyjabber.stream.StreamHandler import StreamHandler, Signal
# from pyjabber.stream.server.StanzaServerHandler import StanzaServerHandler
# from pyjabber.stream.server.StreamServerHandler import StreamServerHandler
# from pyjabber.utils import ClarkNotation as CN
#
#
# class StreamState(Enum):
#     """
#     Stream connection states.
#     """
#     CONNECTED = 0
#     READY = 1
#
#
# class XMLServerParser(ContentHandler):
#     """
#     Manages the stream data and process the XML objects.
#     Inheriting from sax.ContentHandler
#     """
#
#     __slots__ = [
#         "_state",
#         "_buffer",
#         "_streamHandler",
#         "_stanzaHandler",
#         "_stack",
#         "_jid",
#         "_serverJid"
#     ]
#
#     def __init__(self, jid, buffer, starttls):
#         super().__init__()
#         self._jid = jid
#         self._state = StreamState.CONNECTED
#         self._buffer = buffer
#         self._streamHandler = StreamServerHandler(self._buffer, starttls)
#         self._stanzaHandler = StanzaServerHandler(self._buffer)
#
#         self._stack = []
#         self._jid = None
#         self._serverJid = None
#
#         """
#             Init stream by sending stream message
#             Now, pyjabber must act like a client
#         """
#         self.initial_stream()
#
#     @property
#     def buffer(self) -> BaseProtocol:
#         return self._buffer
#
#     @buffer.setter
#     def buffer(self, value: BaseProtocol):
#         self._buffer = value
#         self._streamHandler.buffer = value
#
#     def startElementNS(self, name, qname, attrs):
#         logger.debug(f"Start element NS: {name}")
#
#         clark = CN.clarkFromTuple(name)
#         if CN.clarkFromTuple(name) == '{http://etherx.jabber.org/streams}stream' and self._stack:
#             # ERROR Stream already present in stack
#             raise Exception()
#
#         elem = ET.Element(
#             CN.clarkFromTuple(name),
#             attrib={CN.clarkFromTuple(key): item for key, item in dict(attrs).items()}
#         )
#         self._stack.append(elem)
#
#     def endElementNS(self, name, qname):
#         logger.debug(f"End element NS: {qname} : {name}")
#
#         if name == "</stream:stream>":
#             self._buffer.write(b'</stream>')
#             self._stack.clear()
#             return
#
#         if not self._stack:
#             raise Exception()
#
#         elem = self._stack.pop()
#
#         if elem.tag != CN.clarkFromTuple(name):
#             # INVALID STANZA/MESSAGE
#             raise Exception()
#
#         if self._stack[-1].tag != '{http://etherx.jabber.org/streams}stream':
#             self._stack[-1].append(elem)
#
#         else:
#             if self._state == StreamState.READY:  # Ready to process stanzas
#                 self._stanzaHandler.feed(elem)
#             else:
#                 signal = self._streamHandler.handle_open_stream(elem)
#                 if signal == Signal.RESET:
#                     self._stack.clear()
#                     self.initial_stream()
#                 elif signal == Signal.DONE:
#                     self._state = StreamState.READY
#
#     def characters(self, content: str) -> None:
#         if not self._stack:
#             raise Exception()
#
#         elem = self._stack[-1]
#         if len(elem) != 0:
#             child = elem[-1]
#             child.tail = (child.tail or '') + content
#
#         else:
#             elem.text = (elem.text or '') + content
#
#     def initial_stream(self):
#         initial_stream = Stream.Stream(
#             from_=None,
#             to=self._jid,
#             xmlns=Stream.Namespaces.SERVER.value
#         )
#
#         initial_stream = initial_stream.open_tag()
#         print(initial_stream)
#         self._buffer.write(initial_stream)
