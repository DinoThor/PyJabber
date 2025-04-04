import sqlite3

from pyjabber.metadata import database_path, database_in_memory


def connection() -> sqlite3.Connection:
    """
    Returns an already crafted connection with the database.
    It takes the parameters from the server class instance (i.e., DB path | DB in memory)
    """
    if database_in_memory.get() is not None:
        return sqlite3.connect("file::memory:?cache=shared", uri=True)
    return sqlite3.connect(database_path.get())
