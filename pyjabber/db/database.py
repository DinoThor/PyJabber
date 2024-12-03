import sqlite3

# from pyjabber.metadata import Metadata
from pyjabber.metadata import database_path

def connection() -> sqlite3.Connection:
    return sqlite3.connect(database_path.get())
