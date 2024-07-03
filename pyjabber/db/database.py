import os
import sqlite3


def connection() -> sqlite3.Connection:
    dname = os.path.dirname(os.path.abspath(__file__))
    return sqlite3.connect(dname + '/server.db')
