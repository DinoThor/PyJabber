from unittest.mock import patch

import pytest
import sqlite3
import xml.etree.ElementTree as ET

from sqlalchemy import create_engine, insert

from pyjabber.db.model import Model
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.JID import JID


@pytest.fixture(scope='function')
def setup_database():
    engine = create_engine("sqlite:///:memory:")
    Model.server_metadata.create_all(engine)
    con = engine.connect()
    con.execute(insert(Model.Roster).values(
        [
            {
                "jid": "jid1",
                "roster_item": '<item jid="jid1" name="name1" subscription="both"/>'
            }, {
                "jid": "jid2",
                "roster_item": '<item jid="jid2" name="name2" subscription="both"/>'
            }
        ]
    ))
    con.commit()
    yield engine
    con.close()


@pytest.fixture
def setup(setup_database):
    with patch('pyjabber.plugins.roster.Roster.DB') as mock_db, \
         patch('pyjabber.plugins.roster.Roster.metadata') as mock_meta:
        mock_db.connection = lambda: setup_database.connect()
        mock_meta.HOST = 'localhost'
        yield Roster()


def test_feed_invalid_xml(setup):
    roster = setup

    # Crear un elemento XML inválido (más de un hijo)
    element = ET.Element('element')
    child1 = ET.SubElement(element, 'child')
    child2 = ET.SubElement(element, 'child')

    # Verificar que se devuelve un error de XML inválido
    result = roster.feed(JID('jid1@localhost'), element)
    assert result == SE.invalid_xml()


def test_feed_handle_get(setup):
    roster = setup

    # Mock del manejador 'get'
    def mock_handle_get(jid, element):
        return '<result />'

    roster._handlers['get'] = mock_handle_get

    # Crear un elemento XML válido
    element = ET.Element('iq', attrib={'type': 'get'})
    child = ET.SubElement(element, 'query')

    # Verificar que el manejador 'get' se llama correctamente
    result = roster.feed(JID('jid1@localhost'), element)
    assert result == '<result />'


def test_handleGet_existing_jid(setup):
    roster = setup

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'get'})

    result = roster.handle_get(JID('jid1@localhost'), element)

    assert b'<iq id="1234" type="result">' in result  # Verificamos que el resultado contiene la respuesta IQ correcta


def test_handleGet_non_existing_jid(setup):
    roster = setup
    element = ET.Element('iq', attrib={'id': '1234', 'type': 'get'})

    result = roster.handle_get(JID('non_existing_jid@localhost'), element)

    assert b'<iq id="1234" type="result">' in result  # Verificamos que se maneja adecuadamente aunque el jid no exista


###########
#Handle SET
###########

def test_handleSet_add_new_item(setup):
    roster = setup
    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    # Definimos correctamente el elemento 'query' con el espacio de nombres correcto
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    ET.SubElement(query, '{jabber:iq:roster}item',
                         attrib={'jid': 'jid3', 'name': 'name3', 'subscription': 'both'})

    result = roster.handle_set(JID('jid3@localhost'), element)

    assert b'<iq id="1234" type="result" />' in result


def test_handleSet_update_existing_item(setup):
    roster = setup

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    # Definimos correctamente el elemento 'query' con el espacio de nombres correcto
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    item = ET.SubElement(query, '{jabber:iq:roster}item',
                         attrib={'jid': 'jid3', 'name': 'name3', 'subscription': 'both'})

    result = roster.handle_set(JID('jid1@localhost'), element)

    assert b'<iq id="1234" type="result" />' in result


def test_handleSet_remove_item(setup):
    roster = setup

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    # Definimos correctamente el elemento 'query' con el espacio de nombres correcto
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    item = ET.SubElement(query, '{jabber:iq:roster}item',
                         attrib={'jid': 'jid3', 'name': 'name3', 'subscription': 'both'})

    result = roster.handle_set(JID('jid1@localhost'), element)

    assert b'<iq id="1234" type="result" />' in result


def test_handleSet_invalid_xml(setup):
    roster = setup

    # Create an element with multiple items
    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    ET.SubElement(query, '{jabber:iq:roster}item', attrib={'jid': 'jid1', 'subscription': 'both'})
    ET.SubElement(query, '{jabber:iq:roster}item', attrib={'jid': 'jid2', 'subscription': 'none'})

    res = roster.handle_set(JID('jid1@localhost'), element)
    assert res == SE.invalid_xml()


def test_handleSet_missing_query(setup):
    roster = setup

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})

    res = roster.handle_set(JID('jid1@localhost'), element)
    assert res == SE.invalid_xml()


def test_handleSet_no_items(setup):
    roster = setup

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    query = ET.SubElement(element, '{jabber:iq:roster}query')

    res = roster.handle_set(JID('jid1@localhost'), element)
    assert res == SE.invalid_xml()
