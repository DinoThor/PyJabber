import os
from sqlite3 import Connection
from unittest.mock import patch, MagicMock

from pyjabber.db.database import DB


def test_setup_database_in_memory():
    with patch('pyjabber.db.database.metadata') as mock_meta, \
         patch('pyjabber.db.database.logger') as mock_log, \
         patch('pyjabber.db.database.os') as mock_os, \
         patch('pyjabber.db.database.DB.init_metadata') as mock_init:
        mock_meta.DATABASE_IN_MEMORY = True
        db = DB()
        db.init_metadata = MagicMock()
        db.setup_database()

        assert db._engine is not None
        mock_init.assert_called_with(db._engine)
        mock_os.path.isfile.assert_not_called()


def test_setup_database_local():
    with patch('pyjabber.db.database.metadata') as mock_meta, \
         patch('pyjabber.db.database.DB.init_metadata') as mock_init:
        mock_meta.DATABASE_IN_MEMORY = False
        mock_meta.DATABASE_PURGE = False
        mock_meta.DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_database.db')
        db = DB()
        db.init_metadata = MagicMock()
        db.setup_database()

        assert db._engine is not None
        mock_init.assert_not_called()

def test_setup_database_purge():
    if os.path.isfile('./pyjabber.db'):
        os.remove('./pyjabber.db')

    with patch('pyjabber.db.database.metadata') as mock_metadata, \
         patch('pyjabber.db.database.os') as mock_os, \
         patch('pyjabber.db.database.__version__', '0.2.5'):
        mock_os.path.isfile.return_value = True
        mock_os.remove = MagicMock()
        mock_metadata.database_path.get.return_value = './pyjabber.db'
        mock_metadata.database_in_memory.get.return_value = None
        setup_database(database_path='./pyjabber.db', database_purge=True, sql_init_script='./pyjabber/db/schema.sql')

        mock_os.remove.assert_called_with('./pyjabber.db')
        assert os.path.isfile('./pyjabber.db')
        os.remove('./pyjabber.db')
