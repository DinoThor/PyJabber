import pytest
import sqlite3
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock
from pyjabber.plugins.roster.Roster import Roster  # Ajusta la importación según sea necesario
from pyjabber.stanzas.error import StanzaError as SE  # Ajusta la importación según sea necesario

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
def test_retriveRoster_existing_jid(db_connection_factory):
    roster = Roster(db_connection_factory)
    result = roster.retriveRoster('jid1')
    assert result == [
        (1, 'jid1', '<item jid="jid1" name="name1" subscription="both"/>')
    ]



def test_retriveRoster_non_existing_jid(db_connection_factory):
    roster = Roster(db_connection_factory)
    result = roster.retriveRoster('non_existing_jid')
    assert result == []


def test_update(db_connection_factory):
    roster = Roster(db_connection_factory)

    # Crear un nuevo elemento XML para la actualización
    new_item = ET.Element('item', attrib={'jid': 'jid1', 'name': 'new_name', 'subscription': 'both'})

    result = roster.update(1, new_item)

    assert result == '<item jid="jid1" name="new_name" subscription="both" />'



def test_feed_invalid_xml(db_connection_factory):
    roster = Roster(db_connection_factory)

    # Crear un elemento XML inválido (más de un hijo)
    element = ET.Element('element')
    child1 = ET.SubElement(element, 'child')
    child2 = ET.SubElement(element, 'child')

    # Verificar que se devuelve un error de XML inválido
    result = roster.feed('jid1', element)
    assert result == SE.invalid_xml()


def test_feed_handle_get(db_connection_factory):
    roster = Roster(db_connection_factory)

    # Mock del manejador 'get'
    def mock_handle_get(element, jid):
        return '<result />'

    roster._handlers['get'] = mock_handle_get

    # Crear un elemento XML válido
    element = ET.Element('iq', attrib={'type': 'get'})
    child = ET.SubElement(element, 'query')

    # Verificar que el manejador 'get' se llama correctamente
    result = roster.feed('jid1', element)
    assert result == '<result />'


def test_handleGet_existing_jid(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'get'})

    result = roster.handleGet(element, 'jid1')

    assert b'<iq id="1234" type="result">' in result  # Verificamos que el resultado contiene la respuesta IQ correcta

def test_handleGet_non_existing_jid(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'get'})

    result = roster.handleGet(element, 'non_existing_jid')

    assert b'<iq id="1234" type="result">' in result  # Verificamos que se maneja adecuadamente aunque el jid no exista


## Este test no funciona. No se devuelve una excepcion cuando no eixste el jid requerido
def test_handleGet_exception_handling(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'get'})

    with pytest.raises(Exception):  # Verificamos que se lanza una excepción en caso de error
        roster.handleGet(element, 'jid_with_error')

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


    result = roster.handleSet(element, 'jid3')

    assert b'<iq id="1234" type="result" />' in result



def test_handleSet_update_existing_item(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    # Definimos correctamente el elemento 'query' con el espacio de nombres correcto
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    item = ET.SubElement(query, '{jabber:iq:roster}item',
                         attrib={'jid': 'jid3', 'name': 'name3', 'subscription': 'both'})


    result = roster.handleSet(element, 'jid1')

    assert b'<iq id="1234" type="result" />' in result


def test_handleSet_remove_item(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    # Definimos correctamente el elemento 'query' con el espacio de nombres correcto
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    item = ET.SubElement(query, '{jabber:iq:roster}item',
                         attrib={'jid': 'jid3', 'name': 'name3', 'subscription': 'both'})


    result = roster.handleSet(element, 'jid1')

    assert b'<iq id="1234" type="result" />' in result
def test_handleSet_invalid_xml(db_connection_factory):
    roster = Roster(db_connection_factory)

    # Create an element with multiple items
    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    query = ET.SubElement(element, '{jabber:iq:roster}query')
    ET.SubElement(query, '{jabber:iq:roster}item', attrib={'jid': 'jid1', 'subscription': 'both'})
    ET.SubElement(query, '{jabber:iq:roster}item', attrib={'jid': 'jid2', 'subscription': 'none'})

    with pytest.raises(Exception):
        roster.handleSet(element, 'jid1')

def test_handleSet_missing_query(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})

    with pytest.raises(Exception):
        roster.handleSet(element, 'jid1')

def test_handleSet_no_items(db_connection_factory):
    roster = Roster(db_connection_factory)

    element = ET.Element('iq', attrib={'id': '1234', 'type': 'set'})
    query = ET.SubElement(element, '{jabber:iq:roster}query')

    with pytest.raises(Exception):
        roster.handleSet(element, 'jid1')
