import os
from unittest.mock import patch, mock_open, MagicMock
import pickle
import xmlschema


def load_schemas():
    SERVER_FILE_PATH = os.path.dirname(os.path.abspath(__file__))

    schemas = {
        'http://jabber.org/protocol/activity': "https://xmpp.org/schemas/activity.xsd",
        'jabber:iq:register': "https://xmpp.org/schemas/iq-register.xsd",
        'jabber:iq:roster': "https://xmpp.org/schemas/roster.xsd",
        'urn:ietf:params:xml:ns:xmpp-bind': "https://xmpp.org/schemas/bind.xsd",
        'jabber:client': "https://xmpp.org/schemas/jabber-client.xsd",
        'jabber:server': "https://xmpp.org/schemas/jabber-server.xsd"
    }

    if os.path.exists(SERVER_FILE_PATH + "/schemas.pkl") is False:
        res = {}
        for ns, url in schemas.items():
            res[ns] = xmlschema.XMLSchema(url)

        with open(SERVER_FILE_PATH + "/schemas.pkl", "wb") as file:
            pickle.dump(res, file)
    return res
@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open)
def test_file_creation(mock_open, mock_exists):
    # Simular que el archivo no existe
    mock_exists.return_value = False

    # Ejecutar la función a testear
    _ = load_schemas()

    # Verificar que el archivo se abre para escribir
    mock_open.assert_called_with((os.path.dirname(os.path.abspath(__file__)) + "/schemas.pkl"), "wb")



@patch('os.path.exists')
def test_schema_loading(mock_exists):
    mock_exists.return_value = False

    res = load_schemas()

    for ns, schema in res.items():
        assert isinstance(schema, xmlschema.XMLSchema)


