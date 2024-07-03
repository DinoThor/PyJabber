import os
import pickle

import xmlschema

SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))

schemas = {
    'http://jabber.org/protocol/activity': "https://xmpp.org/schemas/activity.xsd",
    'jabber:iq:register': "https://xmpp.org/schemas/iq-register.xsd",
    'jabber:iq:roster': "https://xmpp.org/schemas/roster.xsd",
    'urn:ietf:params:xml:ns:xmpp-bind': "https://xmpp.org/schemas/bind.xsd",
    'jabber:client': "https://xmpp.org/schemas/jabber-client.xsd",
    'jabber:server': "https://xmpp.org/schemas/jabber-server.xsd"}

if os.path.exists(SERVER_FILE_PATH + "/schemas.pkl") is False:
    res = {}
    for ns, url in schemas.items():
        res[ns] = xmlschema.XMLSchema(url)

    with open("schemas.pkl", "wb") as file:
        pickle.dump(res, file)
