import os
import sqlite3


def connection() -> sqlite3.Connection:
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)

    return sqlite3.connect(dname + '/server.db')