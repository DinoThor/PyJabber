import asyncio
import logging
import sys

from slixmpp import ClientXMPP

class TestClientBot(ClientXMPP):
    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)
        self.add_event_handler("connection_failed", self.connection_error)
        self.add_event_handler("stream_negotiated", self.start)
        self.add_event_handler("message", self.message)

    async def connection_error(self, event):
        self.error = True
        self.disconnect()

    async def start(self, event):       
        self.send_presence()
        await self.get_roster()
        # self.send_presence_subscription("alice@localhost")


    async def message(self, msg):
        print(f"msg['body']")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    xmpp = TestClientBot("bob@127.0.0.1", "1234")
    xmpp.connect()
    xmpp.process(forever=False)
