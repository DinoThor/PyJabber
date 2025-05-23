import os
import shutil
from sqlite3 import Connection
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine

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
        mock_log.info.assert_called_with("Using database on memory. ANY CHANGE WILL BE LOST AFTER SERVER SHUTDOWN!")
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
    origin = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_database.db')
    copy = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_database_purge.db')

    shutil.copy(origin, copy)

    with patch('pyjabber.db.database.metadata') as mock_meta, \
         patch('pyjabber.db.database.DB.init_metadata') as mock_init, \
         patch('pyjabber.db.database.MetaData') as mock_meta_const:
        mock_meta.DATABASE_IN_MEMORY = False
        mock_meta.DATABASE_PURGE = True
        mock_meta.DATABASE_PATH = copy
        db = DB()
        db.init_metadata = MagicMock()
        db.setup_database()

        assert db._engine is not None
        mock_meta_const.assert_called()
        mock_meta_const().reflect.assert_called_with(bind=db._engine)
        mock_meta_const().drop_all.assert_called_with(bind=db._engine)
        mock_init.assert_called_with(db._engine)

        if os.path.isfile(copy):
            os.remove(copy)


def test_setup_database_new_file():
    new_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_database_new.db')

    try:
        with patch('pyjabber.db.database.metadata') as mock_meta, \
             patch('pyjabber.db.database.logger') as mock_log, \
             patch('pyjabber.db.database.create_engine', wraps=create_engine) as spy_engine, \
             patch('pyjabber.db.database.DB.init_metadata', wraps=DB.init_metadata) as spy_init:
            mock_meta.DATABASE_IN_MEMORY = False
            mock_meta.DATABASE_PATH = new_file

            db = DB()
            db.init_metadata = MagicMock()
            db.setup_database()

            assert db._engine is not None
            mock_log.info.assert_called_with("No database found. Initializing one...")
            spy_engine.assert_called_with(f"sqlite:///{new_file}")
            spy_init.assert_called_with(db._engine)
            assert os.path.isfile(new_file)

    finally:
        db._engine.dispose()
        del db
        if os.path.isfile(new_file):
            os.remove(new_file)
