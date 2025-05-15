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
    def connection() -> sqlalchemy.Connection:
        """
        Returns an already crafted connection with the database.
        It takes the parameters from the server class instance (i.e., DB path | DB in memory)
        """
        # if metadata.DATABASE_IN_MEMORY is False:
        #     return sqlite3.connect("file::memory:?cache=shared", uri=True)
        # return sqlite3.connect(metadata.database_path.get())
        return DB._engine.connect()

    @staticmethod
    def setup_database() -> None:
        if metadata.DATABASE_IN_MEMORY:
            logger.info("Using database on memory. ANY CHANGE WILL BE LOST AFTER SERVER SHUTDOWN!")
            DB._engine = create_engine("sqlite:///:memory:")
            init_metadata(DB._engine)

        if os.path.isfile(metadata.DATABASE_PATH):
            DB._engine = create_engine(f"sqlite:///{metadata.DATABASE_PATH}")
            if metadata.DATABASE_PURGE:
                purge_md = MetaData()
                purge_md.reflect(bind=DB._engine)
                purge_md.drop_all(bind=DB._engine)
                del purge_md
                init_metadata(DB._engine)

        else:
            logger.info("No database found. Initializing one...")
            DB._engine = create_engine(f"sqlite:///{metadata.DATABASE_PATH}")
            init_metadata(DB._engine)


def init_metadata(engine: Engine):
    server_metadata = MetaData()

    credentials = Table(
        "credentials", server_metadata,
        Column("id", Integer, primary_key=True),
        Column("jid", String, nullable=False),
        Column("hash_pwd", String, nullable=False)
    )

    roster = Table(
        "roster", server_metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("jid", String, nullable=False),
        Column("roster_item", String, nullable=False)
    )

    pubsub = Table(
        "pubsub", server_metadata,
        Column("node", String, primary_key=True),
        Column("owner", String, nullable=False),
        Column("name", String),
        Column("type", String),
        Column("max_items", Integer)
    )

    pubsub_subscribers = Table(
        "pubsub_subscribers", server_metadata,
        Column("node", String, primary_key=True),
        Column("jid", String, primary_key=True),
        Column("subid", String, primary_key=True),
        Column("subscription", String, nullable=False),
        Column("affiliation", String, nullable=False)
    )

    pubsub_items = Table(
        "pubsub_items", server_metadata,
        Column("node", String, primary_key=True),
        Column("publisher", String, nullable=False),
        Column("item_id", String, primary_key=True),
        Column("payload", String, nullable=False)
    )

    pending_subs = Table(
        "pending_subs", server_metadata,
        Column("jid", String, primary_key=True),
        Column("item", String, primary_key=True)
    )

    server_metadata.create_all(engine)
    Model.setup(credentials, roster, pubsub, pubsub_subscribers, pubsub_items, pending_subs)

