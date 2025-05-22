import os

import sqlalchemy
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, MetaData, Engine, text

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
        DB._engine.dispose()

    @staticmethod
    def setup_database() -> Engine:
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

        return DB._engine

    @staticmethod
    def init_metadata(engine: Engine):
        Model.server_metadata.create_all(engine)

    @staticmethod
    def run_db_migrations() -> None:
        cfg = Config()
        cfg.set_main_option("script_location", os.path.join(metadata.ROOT_PATH, '..', 'alembic_local'))
        cfg.set_main_option("sqlalchemy.url", DB.get_database_url_sqlite())
        command.upgrade(cfg, "head")

    @staticmethod
    def get_database_url_sqlite() -> str:
        path = metadata.DATABASE_PATH
        return f"sqlite:///{path}"
