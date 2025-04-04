import os
import socket
import sqlite3
from contextlib import closing

from loguru import logger

from . import metadata
from pyjabber.db.database import connection
from pyjabber.network import CertGenerator


def setup_query_local_ip():
    """Return the local IP of the host machine"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def setup_database(
    database_in_memory: bool,
    database_path: str,
    database_purge: bool,
    sql_init_script: str,
    sql_delete_script: str
):
    if database_in_memory:
        logger.info("Using database on memory. ANY CHANGE WILL BE LOST AFTER SERVER SHUTDOWN!")
        db_in_memory_con = sqlite3.connect("file::memory:?cache=shared", uri=True)
        with open(sql_init_script, "r") as script:
            db_in_memory_con.cursor().executescript(script.read())
            db_in_memory_con.commit()
        metadata.database_in_memory.set(db_in_memory_con)

    elif os.path.isfile(database_path) is False:
        logger.info("No database found. Initializing one...")
        if database_purge:
            logger.info("Ignoring purge database flag. No DB to purge")
        with closing(connection()) as con:
            with open(sql_init_script, "r") as script:
                con.cursor().executescript(script.read())
            con.commit()
    else:
        if database_purge:
            logger.info("Resetting the database to default state...")
            with closing(connection()) as con:
                with open(sql_delete_script, "r") as script:
                    con.cursor().executescript(script.read())
                con.commit()


def setup_certs(host: str, cert_path: str):
    try:
        if CertGenerator.check_hostname_cert_exists(host, cert_path) is False:
            CertGenerator.generate_hostname_cert(host, cert_path)
    except FileNotFoundError as e:
        logger.error(f"{e.__class__.__name__}: Pass an existing directory in your system to load the certs. "
                     f"Closing server")
        raise SystemExit
