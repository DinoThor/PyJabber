import pytest
import sqlite3
import xml.etree.ElementTree as ET
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.JID import JID


@pytest.fixture
def setup_database():
    con = sqlite3.connect(':memory:')
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE roster (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jid VARCHAR(255) NOT NULL,
            rosterItem VARCHAR(255) NOT NULL
        )
    ''')
    cur.execute('''
        INSERT INTO roster (jid, rosterItem) VALUES
        ('jid1', '<item jid="jid1" name="name1" subscription="both"/>'),
        ('jid2', '<item jid="jid2" name="name2" subscription="none"/>')
    ''')
    con.commit()
    yield con
    con.close()


@pytest.fixture
def db_connection_factory(setup_database):
    def factory():
        return setup_database

    return factory


def test_feed_invalid_xml(db_connection_factory):
    roster = Roster(db_connection_factory)

    # Crear un elemento XML inválido (más de un hijo)
    element = ET.Element('element')
    child1 = ET.SubElement(element, 'child')
    child2 = ET.SubElement(element, 'child')

    # Verificar que se devuelve un error de XML inválido
    result = roster.feed(JID('jid1@localhost'), element)
    assert result == SE.invalid_xml()


def test_feed_handle_get(db_connection_factory):
    roster = Roster(db_connection_factory)

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


def test_handleGet_existing_jid(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'get'})

    result = roster.handle_get(JID('jid1@localhost'), element)

    assert b'<iq id="1234" type="result">' in result  # Verificamos que el resultado contiene la respuesta IQ correcta


def test_handleGet_non_existing_jid(db_connection_factory):
    roster = Roster(db_connection_factory)
    element = ET.Element('iq', attrib={'id': '1234', 'type': 'get'})

    result = roster.handle_get(JID('non_existing_jid@localhost'), element)

    assert b'<iq id="1234" type="result">' in result  # Verificamos que se maneja adecuadamente aunque el jid no exista


###########
#Handle SET
###########

def test_handleSet_add_new_item(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    # Definimos correctamente el elemento 'query' con el espacio de nombres correcto
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    item = ET.SubElement(query, '{jabber:iq:roster}item',
                         attrib={'jid': 'jid3', 'name': 'name3', 'subscription': 'both'})

    result = roster.handle_set(JID('jid3@localhost'), element)

    assert b'<iq id="1234" type="result" />' in result


def test_handleSet_update_existing_item(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    # Definimos correctamente el elemento 'query' con el espacio de nombres correcto
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    item = ET.SubElement(query, '{jabber:iq:roster}item',
                         attrib={'jid': 'jid3', 'name': 'name3', 'subscription': 'both'})

    result = roster.handle_set(JID('jid1@localhost'), element)

    assert b'<iq id="1234" type="result" />' in result


def test_handleSet_remove_item(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    # Definimos correctamente el elemento 'query' con el espacio de nombres correcto
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    item = ET.SubElement(query, '{jabber:iq:roster}item',
                         attrib={'jid': 'jid3', 'name': 'name3', 'subscription': 'both'})

    result = roster.handle_set(JID('jid1@localhost'), element)

    assert b'<iq id="1234" type="result" />' in result


def test_handleSet_invalid_xml(db_connection_factory):
    roster = Roster(db_connection_factory)

    # Create an element with multiple items
    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    ET.SubElement(query, '{jabber:iq:roster}item', attrib={'jid': 'jid1', 'subscription': 'both'})
    ET.SubElement(query, '{jabber:iq:roster}item', attrib={'jid': 'jid2', 'subscription': 'none'})

    with pytest.raises(Exception):
        roster.handle_set(JID('jid1@localhost'), element)


def test_handleSet_missing_query(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})

    with pytest.raises(Exception):
        roster.handle_set(JID('jid1@localhost'), element)


def test_handleSet_no_items(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    query = ET.SubElement(element, '{jabber:iq:roster}query')

    with pytest.raises(Exception):
        roster.handle_set(JID('jid1@localhost'), element)
