import contextvars

import pytest
import sqlite3
import base64
import hashlib
from xml.etree import ElementTree as ET
from unittest.mock import patch, MagicMock

import pyjabber.metadata
from pyjabber.features.SASLFeature import SASL, SASLFeature, Signal, MECHANISM, iq_register_result
from pyjabber.stanzas.error import StanzaError as SE

host = contextvars.ContextVar('host')

@pytest.fixture
def setup_database():
    con = sqlite3.connect(':memory:')
    con = sqlite3.connect(':memory:')
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE credentials (
            jid VARCHAR(255) NOT NULL PRIMARY KEY,
            hash_pwd VARCHAR(255) NOT NULL
        )
    ''')
    cur.execute('''
        INSERT INTO credentials (jid, hash_pwd) VALUES
        ('username', ?)
    ''', (hashlib.sha256(b'password').hexdigest(),))
    con.commit()
    yield con
    con.close()


@pytest.fixture
def db_connection_factory(setup_database):
    def factory():
        return setup_database

    return factory

@patch.object(host, 'get', return_value='localhost')
def test_handle_auth_success(db_connection_factory):
    sasl = SASL()
    sasl._db_connection_factory = db_connection_factory
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = base64.b64encode(b'\x00username\x00password').decode('ascii')
    element.text = auth_text

    result = sasl.handleAuth(element)

    assert result == (Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")


@patch('pyjabber.network.ConnectionManager.ConnectionManager')
def test_handle_auth_failure(MockConnectionsManager, db_connection_factory):
    sasl = SASL(MockConnectionsManager())
    sasl._db_connection_factory = db_connection_factory
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = base64.b64encode(b'\x00username\x00wrongpassword').decode('ascii')
    element.text = auth_text

    result = sasl.handleAuth(element)

    assert result == SE.not_authorized()

# @patch.object(Metadata, 'host', new_callable=lambda: 'localhost')
def test_handle_iq_register_conflict(db_connection_factory):
    sasl = SASL(db_connection_factory)
    element = ET.Element("iq", attrib={"type": "set", "id": "123"})
    query = ET.SubElement(element, "{jabber:iq:register}query")
    username = ET.SubElement(query, "{jabber:iq:register}username")
    username.text = "username"
    password = ET.SubElement(query, "{jabber:iq:register}password")
    password.text = "password"

    result = sasl.handleIQ(element)

    assert result == SE.conflict_error("123")

# @patch.object(Metadata, 'host', new_callable=lambda: 'localhost')
def test_get_fields(MockConnectionsManager, db_connection_factory):
    sasl = SASL(db_connection_factory)

    element = ET.Element("{jabber:iq:register}iq", attrib={"type": "get"})
    ET.SubElement(element, "{jabber:iq:register}query")

    response = sasl.feed(element)

    assert response is not None
    assert response == b'<iq xmlns:ns0="jabber:iq:register" type="result"><ns0:query><username /><password /></ns0:query></iq>'

# @patch.object(Metadata, 'host', new_callable=lambda: 'localhost')
def test_handle_iq_register_success(_, db_connection_factory):
    sasl = SASL(db_connection_factory)
    element = ET.Element("iq", attrib={"type": "set", "id": "123"})
    query = ET.SubElement(element, "{jabber:iq:register}query")
    username = ET.SubElement(query, "{jabber:iq:register}username")
    username.text = "new_user"
    password = ET.SubElement(query, "{jabber:iq:register}password")
    password.text = "password"

    result = sasl.handleIQ(element)

    assert result == iq_register_result("123")


def test_sasl_feature():
    mechanisms = [MECHANISM.PLAIN, MECHANISM.SCRAM_SHA_1]
    feature_element = SASLFeature(mechanisms)

    assert feature_element.tag == "mechanisms"
    assert feature_element.attrib == {"xmlns": "urn:ietf:params:xml:ns:xmpp-sasl"}
    assert len(feature_element) == 2
    assert feature_element[0].text == MECHANISM.PLAIN.value
    assert feature_element[1].text == MECHANISM.SCRAM_SHA_1.value


if __name__ == "__main__":
    pytest.main()
