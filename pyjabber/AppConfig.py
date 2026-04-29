import asyncio
import ssl
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from socket import AddressFamily
from typing import List, Optional


@dataclass(frozen=True, slots=True)
class AppConfig:
    host: str
    ip: List[str]
    ssl_context: ssl.SSLContext
    ssl_context_s2s: ssl.SSLContext
    connection_timeout: int
    server_port: int
    family: AddressFamily
    config_path: str
    cert_path: str
    root_path: str
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


app_config: Optional[AppConfig] = None
