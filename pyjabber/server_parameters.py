import json
import os
import pickle
import socket
from dataclasses import dataclass, replace, field

from typing import List, Tuple


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
    plugins: List[str] = field(default_factory=lambda: [
            'http://jabber.org/protocol/disco#info',
            'http://jabber.org/protocol/disco#items',
            'http://jabber.org/protocol/pubsub',
            'http://jabber.org/protocol/pubsub#publish',
            'http://jabber.org/protocol/pubsub#subscribe',
            'http://jabber.org/protocol/pubsub#config-node',
            'http://jabber.org/protocol/pubsub#create-nodes',
            'http://jabber.org/protocol/pubsub#delete-nodes',
            'jabber:iq:register',
            'jabber:x:data',
            'urn:xmpp:ping',
            'jabber:iq:rpc',
    ])

    items: List[tuple] = field(default_factory=lambda: [
        ('pubsub', 'service', 'http://jabber.org/protocol/pubsub')
    ])

    def dump(self, file_path: str):
        with open(file_path, "wb") as data:
            pickle.dump(self, data)

    def update_from_json(self, file_path: str):
        with open(file_path, "r") as file:
            loaded = json.load(file)
            return replace(
                self,
                host=loaded.get('host') or "localhost",
                client_port=loaded.get('client_port', 5222),
                server_port=loaded.get('server_port', 5269),
                server_out_port=loaded.get('server_out_port', 5269),
                family=loaded.get('family', socket.AF_INET),
                connection_timeout=loaded.get('connection_timeout', 60),
                database_path=loaded.get('database_path', os.path.join(os.getcwd(), "pyjabber.db")),
                database_purge=loaded.get('database_purge', False),
                database_in_memory=loaded.get('database_in_memory', False),
                cert_path=loaded.get('cert_path', None),
                message_persistence=loaded.get('message_persistence', True),
                plugins=loaded.get('plugins', []),
                items=[tuple(item) for item in loaded.get('items', [])]
            )

    @staticmethod
    def load(file_path: str):
        with open(file_path, "rb") as data:
            return pickle.load(data)

    @staticmethod
    def from_json(file_path: str):
        with open(file_path, "r") as file:
            loaded = json.load(file)
            return Parameters(
                host=loaded.get('host') or "localhost",
                client_port=loaded.get('client_port', 5222),
                server_port=loaded.get('server_port', 5269),
                server_out_port=loaded.get('server_out_port', 5269),
                family=loaded.get('family', socket.AF_INET),
                connection_timeout=loaded.get('connection_timeout', 60),
                database_path=loaded.get('database_path', os.path.join(os.getcwd(), "pyjabber.db")),
                database_purge=loaded.get('database_purge', False),
                database_in_memory=loaded.get('database_in_memory', False),
                cert_path=loaded.get('cert_path', None),
                message_persistence=loaded.get('message_persistence', True),
                plugins=loaded.get('plugins', []),
                items=[tuple(item) for item in loaded.get('items', [])]
            )
