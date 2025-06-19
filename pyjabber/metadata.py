from socket import AddressFamily
from typing import List

HOST = None
IP = None
CONNECTION_TIMEOUT = None
SERVER_PORT = None
FAMILY = None
CONFIG_PATH = None
CERT_PATH = None
ROOT_PATH = None
DATABASE_PATH = None
DATABASE_IN_MEMORY = None
DATABASE_PURGE = None
MESSAGE_PERSISTENCE = None
VERBOSE = None
PLUGINS = None
ITEMS = None


TLS_QUEUE = None
CONNECTION_QUEUE = None
S2S_OUTGOING_QUEUE = None
MESSAGE_QUEUE = None


def init_config(
    host: str,
    ip: List[str],
    connection_timeout: int,
    server_port: int,
    family: AddressFamily,
    config_path: str,
    cert_path: str,
    root_path:str,
    database_path: str,
    database_in_memory: bool,
    database_purge: bool,
    message_persistence: bool,
    verbose: bool,
    plugins: List[str],
    items: dict
):
    global HOST, IP, CONNECTION_TIMEOUT, SERVER_PORT, FAMILY, CONFIG_PATH, CERT_PATH, ROOT_PATH, DATABASE_PATH, DATABASE_IN_MEMORY, DATABASE_PURGE, MESSAGE_PERSISTENCE, VERBOSE, PLUGINS, ITEMS
    HOST = host
    IP = ip
    CONNECTION_TIMEOUT = connection_timeout
    SERVER_PORT = server_port
    FAMILY = family
    CONFIG_PATH = config_path
    CERT_PATH = cert_path
    ROOT_PATH = root_path
    DATABASE_PATH = database_path
    DATABASE_IN_MEMORY = database_in_memory
    DATABASE_PURGE = database_purge
    MESSAGE_PERSISTENCE = message_persistence
    VERBOSE = verbose
    PLUGINS = plugins
    ITEMS = items
