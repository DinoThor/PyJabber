import sqlite3

from pyjabber.metadata import Metadata


def connection() -> sqlite3.Connection:
    return sqlite3.connect(Metadata().database_path)
