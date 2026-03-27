import json
import os
import pickle
import socket
from dataclasses import dataclass, field, replace
from typing import Dict, List


@dataclass(frozen=True, slots=True)
class Parameters:
    host: str = "localhost"
    client_port: int = 5222
    server_port: int = 5269
    family: socket.AddressFamily = socket.AF_INET
    connection_timeout: int = 60
    database_path: str = os.path.join(os.getcwd(), "pyjabber.db")
    database_purge: bool = False
    database_in_memory: bool = False
    database_debug: bool = False
    cert_path: str = None
    message_persistence: bool = True
    verbose: bool = False
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
            'urn:xmpp:http:upload:0'
    ])

    items: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        'pubsub.$': {
            "name": "Pubsub Service",
            "category": "pubsub",
            "type": "service",
            "var": "http://jabber.org/protocol/pubsub",
            "extra": {}
        },
        'upload.$': {
            "name": "HTTP File Upload",
            "category": "store",
            "type": "file",
            "var": "urn:xmpp:http:upload:0",
            "extra": {
                "max-size": 5242880
            }
        }
    })
