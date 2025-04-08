import json
import os
import socket
from unittest.mock import mock_open, patch

from pyjabber.server_parameters import Parameters, from_json, load


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
    datamock = {
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
        'message_persistence': False
    }
    m = mock_open(read_data=json.dumps(datamock))

    with patch("pyjabber.server_parameters.open", m):
        param = from_json("fake.json")

    assert param.host == datamock["host"]
    assert param.client_port == datamock["client_port"]
    assert param.server_port == datamock["server_port"]
    assert param.server_out_port == datamock["server_out_port"]
    assert param.family == datamock["family"]
    assert param.connection_timeout == datamock["connection_timeout"]
    assert param.database_path == datamock["database_path"]
    assert param.database_purge is datamock["database_purge"]
    assert param.database_in_memory is datamock["database_in_memory"]
    assert param.cert_path == datamock["cert_path"]
    assert param.message_persistence is datamock["message_persistence"]

def test_update_from_json():
    datamock = {
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
        'message_persistence': False
    }
    m = mock_open(read_data=json.dumps(datamock))

    with patch("pyjabber.server_parameters.open", m):
        param = Parameters().update_from_json("fake.json")

    assert param.host == datamock["host"]
    assert param.client_port == datamock["client_port"]
    assert param.server_port == datamock["server_port"]
    assert param.server_out_port == datamock["server_out_port"]
    assert param.family == datamock["family"]
    assert param.connection_timeout == datamock["connection_timeout"]
    assert param.database_path == datamock["database_path"]
    assert param.database_purge is datamock["database_purge"]
    assert param.database_in_memory is datamock["database_in_memory"]
    assert param.cert_path == datamock["cert_path"]
    assert param.message_persistence is datamock["message_persistence"]


def test_pickle():
    filepath = './params.pkl'
    param = Parameters()
    param.dump(filepath)

    assert os.path.exists(filepath)

    parsed_param = load(filepath)

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

    if os.path.exists(filepath):
        os.remove(filepath)
