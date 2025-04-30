import os
from sqlite3 import Connection
from unittest.mock import patch, MagicMock

from pyjabber.db.database import setup_database, connection


def test_connection():
    with patch('pyjabber.db.database.metadata') as mock_metadata:
        mock_metadata.database_in_memory.get.return_value = MagicMock()
        con = connection()
        assert con is not None
        assert type(con) is Connection
        con.close()

        mock_metadata.database_in_memory.get.return_value = None
        mock_metadata.database_path.get.return_value = './pyjabber.db'
        con = connection()
        assert con
        assert type(con) is Connection
        assert os.path.isfile('./pyjabber.db')
        con.close()
        os.remove('./pyjabber.db')

def test_setup_database_in_memory():
    print(os.getcwd())
    with patch('pyjabber.db.database.metadata') as mock_metadata, \
         patch('pyjabber.db.database.__version__', '0.2.5'):
        mock_metadata.database_in_memory.return_value = MagicMock()
        setup_database(database_in_memory=True, sql_init_script='../pyjabber/db/schema.sql')


def test_setup_database_local():
    with patch('pyjabber.db.database.metadata') as mock_metadata, \
         patch('pyjabber.db.database.__version__', '0.2.5'):
        mock_metadata.database_path.get.return_value = './pyjabber.db'
        mock_metadata.database_in_memory.get.return_value = None
        setup_database(database_path='./pyjabber.db', sql_init_script='../pyjabber/db/schema.sql')
    assert os.path.isfile('./pyjabber.db')
    os.remove('./pyjabber.db')
