import logging
import os

import sqlalchemy
from alembic import command
from alembic.config import Config
from loguru import logger
from sqlalchemy import StaticPool, event
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from pyjabber.AppConfig import AppConfig
from pyjabber.db.model import Model


class DB:
    _engine = None

    @staticmethod
    def connection() -> sqlalchemy.Connection:  #pragma: no cover
        """
        Returns an already crafted connection with the database.
        It takes the parameters from the server class instance (i.e., DB path | DB in memory)
        """
        return DB._engine.connect()

    @staticmethod
    async def connection_async() -> AsyncConnection:  # pragma: no cover
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
    async def setup_database() -> AsyncEngine:
        """
        Initialize the database that will be used in the server session.
        It can be adjusted by the parameters passed in the Server constructor, as it will be
        read via the metadata class
        :return: SQLAlchemy Engine
        """
        if not AppConfig.database_debug:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
            logging.getLogger("sqlite3").setLevel(logging.WARNING)
            logging.getLogger("aiosqlite").setLevel(logging.WARNING)

        if AppConfig.database_in_memory:
            logger.info("Using database on memory. ANY CHANGE WILL BE LOST AFTER SERVER SHUTDOWN!")
            DB._engine = create_async_engine(
                url="sqlite+aiosqlite:///:memory:",
                isolation_level="AUTOCOMMIT",
                poolclass=StaticPool,
                echo=AppConfig.database_debug
            )

            @event.listens_for(DB._engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA synchronous=FULL")
                cursor.execute("PRAGMA journal_mode=MEMORY")
                cursor.close()

            await DB._init_metadata(DB._engine)
            return DB._engine

        if os.path.isfile(AppConfig.database_path):
            DB._engine = create_async_engine(
                url="sqlite+aiosqlite:///tickets.db",
                echo=AppConfig.database_debug
            )

        else:
            logger.info("No database found. Initializing one...")
            DB._engine = create_async_engine(
                f"sqlite+aiosqlite:///{AppConfig.database_path}",
                echo=AppConfig.database_debug
            )

        @event.listens_for(DB._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-20000")
            cursor.close()

        await DB._init_metadata(DB._engine)
        return DB._engine

    @staticmethod
    async def _init_metadata(engine: AsyncEngine):
        def sync_create_all(connection):
            Model.server_metadata.create_all(connection)

        async with engine.begin() as conn:
            await conn.run_sync(sync_create_all)

    @staticmethod
    def run_db_migrations() -> None:
        cfg = Config()
        cfg.set_main_option("script_location", os.path.join(AppConfig.root_path, '..', 'alembic_local'))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{AppConfig.database_path}")
        command.upgrade(cfg, "head")
