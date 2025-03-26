import ssl

import pytest

from slixmpp import ClientXMPP
from slixmpp.exceptions import IqError, IqTimeout


@pytest.fixture
def dummy_client():
    jid = "dummy@localhost"
    client = ClientXMPP(jid, "1234")

    client.ssl_context.check_hostname = False
    client.ssl_context.verify_mode = ssl.CERT_NONE

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    client.add_event_handler("session_start", session_start)

    async def register(self, event):
        resp = self.Iq()
        resp["type"] = "set"
        resp["register"]["username"] = self.boundjid.user
        resp["register"]["password"] = self.password

        try:
            await resp.send()
        except IqError:
            """
                If the user is already registered, it will return an IQ error
                We can safely ignore it. The client will try the auth process
                right after the ibr process
            """
            pass
        except IqTimeout:
            raise Exception("Timeout error during the register process.")

    client.add_event_handler("register", register)
    client.register_plugin("xep_0077")

    yield jid, client

    client.disconnect()
