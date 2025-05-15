import logging
import os
import sqlite3
from contextlib import closing
from sqlite3 import Connection
from typing import Optional

import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Engine, BINARY

from pyjabber import __version__
from pyjabber import metadata
from loguru import logger

from pyjabber.db.model import Model


class DB:
    _engine: sqlalchemy.Engine = None

    @staticmethod
    def connection() -> sqlalchemy.Connection:  #pragma: no cover
        """
        Returns an already crafted connection with the database.
        It takes the parameters from the server class instance (i.e., DB path | DB in memory)
        """
        return DB._engine.connect()

    @staticmethod
    def setup_database() -> None:
        if metadata.DATABASE_IN_MEMORY:
            logger.info("Using database on memory. ANY CHANGE WILL BE LOST AFTER SERVER SHUTDOWN!")
            DB._engine = create_engine("sqlite:///:memory:")
            DB.init_metadata(DB._engine)

        elif os.path.isfile(metadata.DATABASE_PATH):
            DB._engine = create_engine(f"sqlite:///{metadata.DATABASE_PATH}")
            if metadata.DATABASE_PURGE:
                purge_md = MetaData()
                purge_md.reflect(bind=DB._engine)
                purge_md.drop_all(bind=DB._engine)
                del purge_md
                DB.init_metadata(DB._engine)

        else:
            logger.info("No database found. Initializing one...")
            DB._engine = create_engine(f"sqlite:///{metadata.DATABASE_PATH}")
            DB.init_metadata(DB._engine)

    @staticmethod
    def init_metadata(engine: Engine):
        Model.server_metadata.create_all(engine)

