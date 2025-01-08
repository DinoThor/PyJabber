import sqlite3

from pyjabber.metadata import database_path, database_in_memory


def connection() -> sqlite3.Connection:
    if database_in_memory:
        return sqlite3.connect("file::memory:?cache=shared", uri=True)
    return sqlite3.connect(database_path.get())
