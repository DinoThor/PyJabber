import sqlite3

DB_PATH = "./pyjabber/db/server.db"

def connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)