import json
import os
import socket
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Parameters:
    host: str = "localhost"
    client_port: int = 5222
    server_port: int = 5269
    server_out_port: int = 5269
    family: socket.AddressFamily = socket.AF_INET
    connection_timeout: int = 60
    database_path: str = os.path.join(os.getcwd(), "pyjabber.db")
    database_purge: bool = False
    database_in_memory: bool = False
    cert_path: str = None
    message_persistence: bool = True

    def from_json(self, file_path: str):
        with open(file_path, "r") as file:
            loaded = json.load(file)
            return replace(
                self,
                host=loaded.get('host') or "localhost",
                client_port=loaded.get('client_port') or 5222,
                server_port=loaded.get('server_port') or 5269,
                server_out_port=loaded.get('server_out_port') or 5269,
                family=loaded.get('family') or socket.AF_INET,
                connection_timeout=loaded.get('connection_timeout') or 60,
                database_path=loaded.get('database_path') or os.path.join(os.getcwd(), "pyjabber.db"),
                database_purge=loaded.get('database_purge') or False,
                database_in_memory=loaded.get('database_in_memory') or False,
                cert_path=loaded.get('cert_path') or None,
                message_persistence=loaded.get('message_persistence') is True
            )
