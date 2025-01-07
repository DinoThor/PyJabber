import sqlite3

from pyjabber.metadata import database_path, database_on_memory


def connection() -> sqlite3.Connection:
    if database_on_memory is None:
        return sqlite3.connect(database_path.get())
    return sqlite3.connect('file::memory:?cache=shared')
