import os

import sqlalchemy
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, MetaData, Engine

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
    def close_engine():
        """
        Safely dispose the global engine instance used across the server
        """
        DB._engine.dispose()

    @staticmethod
    def setup_database() -> Engine:
        """
        Initialize the database that will be used in the server session.
        It can be adjusted by the parameters passed in the Server constructor, as it will be
        read via the metadata class
        :return: SQLAlchemy Engine
        """
        if metadata.DATABASE_IN_MEMORY:
            logger.info("Using database on memory. ANY CHANGE WILL BE LOST AFTER SERVER SHUTDOWN!")
            DB._engine = create_engine("sqlite:///:memory:")
            DB._init_metadata(DB._engine)

        elif os.path.isfile(metadata.DATABASE_PATH):
            DB._engine = create_engine(f"sqlite:///{metadata.DATABASE_PATH}")
            if metadata.DATABASE_PURGE:
                purge_md = MetaData()
                purge_md.reflect(bind=DB._engine)
                purge_md.drop_all(bind=DB._engine)
                del purge_md
                DB._init_metadata(DB._engine)

        else:
            logger.info("No database found. Initializing one...")
            DB._engine = create_engine(f"sqlite:///{metadata.DATABASE_PATH}")
            DB._init_metadata(DB._engine)

        return DB._engine

    @staticmethod
    def _init_metadata(engine: Engine):
        Model.server_metadata.create_all(engine)

    @staticmethod
    def run_db_migrations() -> None:
        cfg = Config()
        cfg.set_main_option("script_location", os.path.join(metadata.ROOT_PATH, '..', 'alembic_local'))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{metadata.DATABASE_PATH}")
        command.upgrade(cfg, "head")
