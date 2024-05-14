import asyncio
import logging
import sys

from slixmpp import ClientXMPP


class TestClientBot(ClientXMPP):
    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)
        self.add_event_handler("connection_failed", self.connection_error)
        self.add_event_handler("stream_negotiated", self.stream_negotiated)
        # self.add_event_handler("roster_update", self.start)
        self.add_event_handler("message", self.message)
        # self.error = False

    async def connection_error(self, event):
        self.error = True
        self.disconnect()

    async def stream_negotiated(self, event):
        self.send_presence()
        await self.get_roster()
        if sys.argv[1] == "t":
            self.send_presence_subscription("testing1@localhost")
        

    async def start(self, event):       
        pass
        await asyncio.sleep(2)
        if sys.argv[1] == "t":
                self.send_message(
                    mto = "demo@localhost",
                    mfrom = self.boundjid.bare,
                    mbody = "Hola! soy Test",
                    mtype = "chat"
                )

    async def message(self, msg):
        print(f"Mensaje recibido de {msg['from']} ===> {msg['body']}")
        await asyncio.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    if sys.argv[1] == "t":
        xmpp = TestClientBot("test@127.0.0.1", "1234")
    else:    
        xmpp = TestClientBot("testing1@127.0.0.1", "1234")
    xmpp.register_plugin('xep_0077')
    xmpp.connect()
    xmpp.process(forever=False)
