import pytest
import sqlite3
import base64
import hashlib
from xml.etree import ElementTree as ET
from unittest.mock import MagicMock, patch

from pyjabber.features.SASLFeature import SASL, SASLFeature, Signal, mechanismEnum
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.utils import ClarkNotation as CN


@pytest.fixture
def setup_database():
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


@patch('pyjabber.network.ConnectionManager.ConnectionManager')
def test_handle_auth_success(MockConnectionsManager, db_connection_factory):
    sasl = SASL()
    sasl._connections = MockConnectionsManager()
    sasl._db_connection_factory = db_connection_factory
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = base64.b64encode(b'\x00username\x00password').decode('ascii')
    element.text = auth_text

    result = sasl.handleAuth(element)

    assert result == (Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")


@patch('pyjabber.network.ConnectionManager.ConnectionManager')
def test_handle_auth_failure(MockConnectionsManager, db_connection_factory):
    sasl = SASL()
    sasl._connections = MockConnectionsManager()
    sasl._db_connection_factory = db_connection_factory
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = base64.b64encode(b'\x00username\x00wrongpassword').decode('ascii')
    element.text = auth_text

    result = sasl.handleAuth(element)

    assert result == SE.not_authorized()

def test_handle_iq_register_conflict(db_connection_factory):
    sasl = SASL(db_connection_factory)
    element = ET.Element("iq", attrib={"type": "set", "id": "123"})
    query = ET.SubElement(element, "{jabber:iq:register}query")
    username = ET.SubElement(query, "{jabber:iq:register}username")
    username.text = "username"
    password = ET.SubElement(query, "{jabber:iq:register}password")
    password.text = "password"

    result = sasl.handleIQ(element)

    expected_result = (Signal.RESET, SE.conflict_error("123"))
    assert result == expected_result

def test_handle_iq_register_success(db_connection_factory):
    sasl = SASL(db_connection_factory)
    element = ET.Element("iq", attrib={"type": "set", "id": "123"})
    query = ET.SubElement(element, "{jabber:iq:register}query")
    username = ET.SubElement(query, "{jabber:iq:register}username")
    username.text = "new_user"
    password = ET.SubElement(query, "{jabber:iq:register}password")
    password.text = "password"

    result = sasl.handleIQ(element)

    expected_result = sasl.iq_register_result("123")
    assert result == (Signal.RESET, expected_result)


def test_sasl_feature():
    mechanisms = [mechanismEnum.PLAIN, mechanismEnum.SCRAM_SHA_1]
    feature_element = SASLFeature(mechanisms)

    assert feature_element.tag == "mechanisms"
    assert feature_element.attrib == {"xmlns": "urn:ietf:params:xml:ns:xmpp-sasl"}
    assert len(feature_element) == 2
    assert feature_element[0].text == mechanismEnum.PLAIN.value
    assert feature_element[1].text == mechanismEnum.SCRAM_SHA_1.value


if __name__ == "__main__":
    pytest.main()
