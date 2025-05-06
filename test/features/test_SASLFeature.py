import contextvars
from sqlite3 import Connection

import bcrypt
import pytest
import sqlite3
import base64
import hashlib
from xml.etree import ElementTree as ET
from unittest.mock import patch

from pyjabber.features.SASLFeature import SASL, SASLFeature, Signal, MECHANISM, iq_register_result
from pyjabber.stanzas.error import StanzaError as SE

host = contextvars.ContextVar('host')

@pytest.fixture(scope="function")
def setup_database() -> Connection:
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
    ''',  (bcrypt.hashpw(b'password', bcrypt.gensalt()),))
    con.commit()
    yield con
    con.close()


def test_handle_auth_success(setup_database):
    sasl = SASL()
    sasl._db_connection_factory = lambda : setup_database
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = base64.b64encode(b'\x00username\x00password').decode('ascii')
    element.text = auth_text

    with patch('pyjabber.features.SASLFeature.host') as mock_host:
        mock_host.get.return_value = 'localhost'
        result = sasl.handleAuth(element)

    assert result == (Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")


@patch('pyjabber.network.ConnectionManager.ConnectionManager')
def test_handle_auth_failure(setup_database):
    sasl = SASL()
    sasl._db_connection_factory = lambda : setup_database
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = base64.b64encode(b'\x00username\x00wrongpassword').decode('ascii')
    element.text = auth_text

    with patch('pyjabber.features.SASLFeature.host') as mock_host:
        mock_host.get.return_value = 'localhost'
        result = sasl.handleAuth(element)

    assert result == SE.not_authorized()


def test_handle_iq_register_conflict(setup_database):
    sasl = SASL()
    sasl._db_connection_factory = lambda : setup_database
    element = ET.Element("iq", attrib={"type": "set", "id": "123"})
    query = ET.SubElement(element, "{jabber:iq:register}query")
    username = ET.SubElement(query, "{jabber:iq:register}username")
    username.text = "username"
    password = ET.SubElement(query, "{jabber:iq:register}password")
    password.text = "password"

    with patch('pyjabber.stanzas.error.StanzaError.host') as mock_host:
        mock_host.get.return_value = 'localhost'
        result = sasl.handleIQ(element)

        assert result == SE.conflict_error("123")

def test_get_fields(setup_database):
    sasl = SASL()
    sasl._db_connection_factory = lambda : setup_database

    element = ET.Element("{jabber:iq:register}iq", attrib={"type": "get", "id": "1234"})
    ET.SubElement(element, "{jabber:iq:register}query")

    response = sasl.feed(element)
    res_elem = ET.fromstring(response)

    assert res_elem is not None
    assert res_elem.tag in element.tag
    assert res_elem.attrib.get('type') == 'result'
    assert res_elem.attrib.get('id') == '1234'
    assert 'query' in res_elem[0].tag
    assert res_elem[0][0].tag == 'username'
    assert res_elem[0][1].tag == 'password'

def test_handle_iq_register_success(setup_database):
    sasl = SASL()
    sasl._db_connection_factory = lambda : setup_database
    element = ET.Element("iq", attrib={"type": "set", "id": "123"})
    query = ET.SubElement(element, "{jabber:iq:register}query")
    username = ET.SubElement(query, "{jabber:iq:register}username")
    username.text = "new_user"
    password = ET.SubElement(query, "{jabber:iq:register}password")
    password.text = "password"

    with patch('pyjabber.features.SASLFeature.host') as mock_host:
        mock_host.get.return_value = 'localhost'
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
