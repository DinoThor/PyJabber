import os.path
from typing import List

HOST = None
IP = None
CONFIG_PATH = None
CERT_PATH = None
ROOT_PATH = None
DATABASE_PATH = None
DATABASE_IN_MEMORY = None
DATABASE_PURGE = None
MESSAGE_PERSISTENCE = None
PLUGINS = None
ITEMS =None

TLS_QUEUE = None
CONNECTION_QUEUE = None
MESSAGE_QUEUE = None


def init_config(
    host: str,
    ip: List[str],
    config_path: str,
    cert_path: str,
    root_path:str,
    database_path: str,
    database_in_memory: bool,
    database_purge: bool,
    message_persistence: bool,
    plugins: List[str],
    items: List[tuple]
):
    global HOST, IP, CONFIG_PATH, CERT_PATH, ROOT_PATH, DATABASE_PATH, DATABASE_IN_MEMORY, DATABASE_PURGE, MESSAGE_QUEUE, MESSAGE_PERSISTENCE, PLUGINS, ITEMS
    HOST = host
    IP = ip
    CONFIG_PATH = config_path
    CERT_PATH = cert_path
    ROOT_PATH = root_path
    DATABASE_PATH = database_path
    DATABASE_IN_MEMORY = database_in_memory
    DATABASE_PURGE = database_purge
    MESSAGE_PERSISTENCE = message_persistence
    PLUGINS = plugins
    ITEMS = items

    global TLS_QUEUE, CONNECTION_QUEUE, MESSAGE_QUEUE

