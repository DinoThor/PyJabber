import os
import sqlite3
from contextlib import closing
from typing import Optional

from pyjabber import __version__
from pyjabber import metadata
from loguru import logger

def connection() -> sqlite3.Connection: # pragma: no cover
    """
    Returns an already crafted connection with the database.
    It takes the parameters from the server class instance (i.e., DB path | DB in memory)
    """
    if metadata.database_in_memory.get() is not None:
        return sqlite3.connect("file::memory:?cache=shared", uri=True)
    return sqlite3.connect(metadata.database_path.get())

def setup_database(
    database_in_memory: bool,
    database_path: str,
    database_purge: bool,
    sql_init_script: str,
):
    if database_in_memory:
        logger.info("Using database on memory. ANY CHANGE WILL BE LOST AFTER SERVER SHUTDOWN!")
        db_in_memory_con = sqlite3.connect("file::memory:?cache=shared", uri=True)
        with open(sql_init_script, "r") as script_template:
            script = script_template.read()
            script = script.replace("{{version}}", f"'{__version__}'")
            db_in_memory_con.cursor().executescript(script)
            db_in_memory_con.commit()
        metadata.database_in_memory.set(db_in_memory_con)

    elif os.path.isfile(database_path) is False:
        logger.info("No database found. Initializing one...")
        if database_purge:
            logger.info("Ignoring purge database flag. No DB to purge")
        with closing(connection()) as con:
            with open(sql_init_script, "r") as script_template:
                script = script_template.read()
                script = script.replace("{{version}}", f"'{__version__}'")
                con.cursor().executescript(script)
            con.commit()
    else:
        if database_purge:
            logger.info("Resetting the database to default state...")
            os.remove(database_path)
            with closing(connection()) as con:
                with open(sql_init_script, "r") as script_template:
                    script = script_template.read()
                    script = script.replace("{{version}}", f"'{__version__}'")
                    con.cursor().executescript(script)
                con.commit()

        else:
            with closing(connection()) as con:
                res = con.execute("SELECT value FROM meta WHERE key = 'version'", ())
                res = res.fetchone()
                version = res[0] if res else None
            migration(version)

def migration(version: Optional[str]):
    if not version:
        return

    # DB migration feature was added in v0.2.6
    # Only changes in the db after v0.2.6 will be taken into account for migration

