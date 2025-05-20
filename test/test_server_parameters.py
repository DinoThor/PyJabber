import json
import os
import socket
from unittest.mock import mock_open, patch

from pyjabber.server_parameters import Parameters


def test_default_parameters():
    param = Parameters()
    assert param.host == "localhost"
    assert param.client_port == 5222
    assert param.server_port == 5269
    assert param.server_out_port == 5269
    assert param.family == socket.AF_INET
    assert param.connection_timeout == 60
    assert param.database_path == os.path.join(os.getcwd(), "pyjabber.db")
    assert param.database_purge is False
    assert param.database_in_memory is False
    assert param.cert_path is None
    assert param.message_persistence is True


def test_from_json():
    data_mock = {
        'host': 'publichost',
        'client_port': 5252,
        'server_port': 2525,
        'server_out_port': 6952,
        'family': socket.AF_INET6.value,
        'connection_timeout': 59,
        'database_path': '/some/fake/path',
        'database_purge': True,
        'database_in_memory': True,
        'cert_path': '/another/fake/path',
        'message_persistence': False,
        'plugins': [
            'http://jabber.org/protocol/disco#info',
            'http://jabber.org/protocol/disco#items'
        ],
        'items': [('pubsub', 'http://jabber.org/protocol/pubsub')]
    }
    m = mock_open(read_data=json.dumps(data_mock))

    with patch("pyjabber.server_parameters.open", m):
        param = Parameters.from_json("fake.json")

    assert param.host == data_mock["host"]
    assert param.client_port == data_mock["client_port"]
    assert param.server_port == data_mock["server_port"]
    assert param.server_out_port == data_mock["server_out_port"]
    assert param.family == data_mock["family"]
    assert param.connection_timeout == data_mock["connection_timeout"]
    assert param.database_path == data_mock["database_path"]
    assert param.database_purge is data_mock["database_purge"]
    assert param.database_in_memory is data_mock["database_in_memory"]
    assert param.cert_path == data_mock["cert_path"]
    assert param.message_persistence is data_mock["message_persistence"]
    assert param.plugins == data_mock["plugins"]
    assert param.items == data_mock["items"]


def test_update_from_json():
    data_mock = {
        'host': 'publichost',
        'client_port':  5252,
        'server_port': 2525,
        'server_out_port': 6952,
        'family': socket.AF_INET6.value,
        'connection_timeout': 59,
        'database_path': '/some/fake/path',
        'database_purge': True,
        'database_in_memory': True,
        'cert_path': '/another/fake/path',
        'message_persistence': False,
        'plugins': [
            'http://jabber.org/protocol/disco#info',
            'http://jabber.org/protocol/disco#items'
        ],
        'items': [('pubsub', 'http://jabber.org/protocol/pubsub')]
    }
    m = mock_open(read_data=json.dumps(data_mock))

    with patch("pyjabber.server_parameters.open", m):
        param = Parameters().update_from_json("fake.json")

    assert param.host == data_mock["host"]
    assert param.client_port == data_mock["client_port"]
    assert param.server_port == data_mock["server_port"]
    assert param.server_out_port == data_mock["server_out_port"]
    assert param.family == data_mock["family"]
    assert param.connection_timeout == data_mock["connection_timeout"]
    assert param.database_path == data_mock["database_path"]
    assert param.database_purge is data_mock["database_purge"]
    assert param.database_in_memory is data_mock["database_in_memory"]
    assert param.cert_path == data_mock["cert_path"]
    assert param.message_persistence is data_mock["message_persistence"]
    assert param.plugins == data_mock["plugins"]
    assert param.items == data_mock["items"]


def test_pickle():
    filepath = './params.pkl'
    param = Parameters()
    param.dump(filepath)

    assert os.path.exists(filepath)

    parsed_param = Parameters.load(filepath)

    assert parsed_param.host == "localhost"
    assert parsed_param.client_port == 5222
    assert parsed_param.server_port == 5269
    assert parsed_param.server_out_port == 5269
    assert parsed_param.family == socket.AF_INET
    assert parsed_param.connection_timeout == 60
    assert parsed_param.database_path == os.path.join(os.getcwd(), "pyjabber.db")
    assert parsed_param.database_purge is False
    assert parsed_param.database_in_memory is False
    assert parsed_param.cert_path is None
    assert parsed_param.message_persistence is True
    assert parsed_param.plugins == [
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
        'jabber:iq:rpc'
    ]
    assert parsed_param.items == [('pubsub', 'service', 'http://jabber.org/protocol/pubsub')]

    if os.path.exists(filepath):
        os.remove(filepath)
