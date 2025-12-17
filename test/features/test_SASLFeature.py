from sqlite3 import Connection

import bcrypt
import pytest
import base64
from xml.etree import ElementTree as ET
from unittest.mock import patch

from sqlalchemy import create_engine, insert

from pyjabber.db.model import Model
from pyjabber.features.SASLFeature import SASL, SASLFeature, Signal, MECHANISM
from pyjabber.stanzas.error import StanzaError as SE


@pytest.fixture(scope="function")
def setup_database() -> Connection:
    engine = create_engine("sqlite:///:memory:")
    Model.server_metadata.create_all(engine)
    con = engine.connect()
    con.execute(insert(Model.Credentials).values({
        "jid": "username",
        "hash_pwd": bcrypt.hashpw(b'password', bcrypt.gensalt())
    }))
    con.commit()

    yield con

    con.close()


@pytest.fixture
def sasl(setup_database):
    with patch('pyjabber.features.SASLFeature.metadata') as mock_meta, \
         patch('pyjabber.features.SASLFeature.DB') as mock_db, \
         patch('pyjabber.features.SASLFeature.ConnectionManager') as mock_con, \
         patch('pyjabber.stanzas.error.StanzaError.metadata') as mock_meta_se:
        mock_db.connection.return_value = setup_database
        mock_meta.HOST = 'localhost'
        mock_meta_se.HOST = 'localhost'
        yield SASL()


def test_handle_auth_success(sasl):
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = base64.b64encode(b'\x00username\x00password').decode('ascii')
    element.text = auth_text

    result = sasl.handle_auth(element)

    assert result == (Signal.RESET, b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")


def test_handle_auth_failure(sasl):
    element = ET.Element("{urn:ietf:params:xml:ns:xmpp-sasl}auth")
    auth_text = base64.b64encode(b'\x00username\x00wrongpassword').decode('ascii')
    element.text = auth_text

    result = sasl.handle_auth(element)

    assert result == SE.not_authorized()


def test_handle_iq_register_conflict(sasl):
    element = ET.Element("iq", attrib={"type": "set", "id": "123"})
    query = ET.SubElement(element, "{jabber:iq:register}query")
    username = ET.SubElement(query, "{jabber:iq:register}username")
    username.text = "username"
    password = ET.SubElement(query, "{jabber:iq:register}password")
    password.text = "password"

    result = sasl.handle_IQ(element)

    assert result == SE.conflict_error("123")


def test_get_fields(sasl):
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


def test_handle_iq_register_success(sasl):
    element = ET.Element("iq", attrib={"type": "set", "id": "123"})
    query = ET.SubElement(element, "{jabber:iq:register}query")
    username = ET.SubElement(query, "{jabber:iq:register}username")
    username.text = "new_user"
    password = ET.SubElement(query, "{jabber:iq:register}password")
    password.text = "password"

    result = sasl.handle_IQ(element)

    assert result == SASL.iq_register_result("123")


def test_sasl_feature():
    mechanisms = [MECHANISM.PLAIN, MECHANISM.SCRAM_SHA_1]
    feature_element = SASLFeature(mechanisms)

    assert feature_element.tag == "mechanisms"
    assert feature_element.attrib == {"xmlns": "urn:ietf:params:xml:ns:xmpp-sasl"}
    assert len(feature_element) == 2
    assert feature_element[0].text == MECHANISM.PLAIN.value
    assert feature_element[1].text == MECHANISM.SCRAM_SHA_1.value


def test_iq_register_result():
    with patch('pyjabber.features.SASLFeature.metadata') as mock_meta:
        mock_meta.HOST = 'localhost'

        res = SASL.iq_register_result("123")
        res_parsed = ET.fromstring(res)

        assert res_parsed.tag == "iq"
        assert res_parsed.attrib["type"] == "result"
        assert res_parsed.attrib["id"] == "123"
        assert res_parsed.attrib["from"] == "localhost"


if __name__ == "__main__":
    pytest.main()
