import pytest
import sqlite3
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock
from pyjabber.plugins.roster.Roster import Roster  # Ajusta la importación según sea necesario
from pyjabber.stanzas.error import StanzaError as SE  # Ajusta la importación según sea necesario

@pytest.fixture(scope='module')
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

@pytest.mark.asyncio
def test_retriveRoster_existing_jid(setup_database):
    db_connection_factory = MagicMock(return_value=setup_database)
    roster = Roster(db_connection_factory)
    result = roster.retriveRoster('jid1')
    assert result == [
        (1, 'jid1', '<item jid="jid1" name="name1" subscription="both"/>')
    ]



@pytest.mark.asyncio
def test_retriveRoster_non_existing_jid(setup_database):
    db_connection_factory = MagicMock(return_value=setup_database)
    roster = Roster(db_connection_factory)
    result = roster.retriveRoster('non_existing_jid')
    assert result == []


@pytest.mark.asyncio
def test_update(setup_database):
    db_connection_factory = MagicMock(return_value=setup_database)


    roster = Roster(db_connection_factory)

    # Crear un nuevo elemento XML para la actualización
    new_item = ET.Element('item', attrib={'jid': 'jid1', 'name': 'new_name', 'subscription': 'both'})

    result = roster.update(1, new_item)

    assert result == '<item jid="jid1" name="new_name" subscription="both" />'



@pytest.mark.asyncio
def test_feed_invalid_xml(setup_database):
    db_connection_factory = MagicMock(return_value=setup_database)
    roster = Roster(db_connection_factory)

    # Crear un elemento XML inválido (más de un hijo)
    element = ET.Element('element')
    child1 = ET.SubElement(element, 'child')
    child2 = ET.SubElement(element, 'child')

    # Verificar que se devuelve un error de XML inválido
    result = roster.feed('jid1', element)
    assert result == SE.invalid_xml()


@pytest.mark.asyncio
def test_feed_handle_get(setup_database):
    db_connection_factory = MagicMock(return_value=setup_database)
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
