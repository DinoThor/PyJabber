import asyncio
import ssl
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from socket import AddressFamily
from typing import List

HOST = None
IP = None
SSL_CONTEXT = None
CONNECTION_TIMEOUT = None
SERVER_PORT = None
FAMILY = None
CONFIG_PATH = None
CERT_PATH = None
ROOT_PATH = None
DATABASE_PATH = None
DATABASE_IN_MEMORY = None
DATABASE_PURGE = None
DATABASE_DEBUG = None
MESSAGE_PERSISTENCE = None
SEMAPHORE = None
PROCESS_POOL_EXE = None
VERBOSE = None
PLUGINS = None
ITEMS = None


TLS_QUEUE = None
CONNECTION_QUEUE = None
S2S_OUTGOING_QUEUE = None
MESSAGE_QUEUE = None

@dataclass(frozen=True, slots=True)
class AppConfig:
    host: str
    ip: List[str]
    ssl_context: ssl.SSLContext
    connection_timeout: int
    server_port: int
    family: AddressFamily
    config_path: str
    cert_path: str
    root_path:str
    database_path: str
    database_in_memory: bool
    database_purge: bool
    database_debug: bool
    message_persistence: bool
    semaphore: asyncio.Semaphore
    process_pool_exe: ProcessPoolExecutor
    verbose: bool
    plugins: List[str]
    items: dict
