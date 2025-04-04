import json
import os
import socket
from unittest.mock import mock_open, patch

from pyjabber.server_parameters import Parameters


def test_default_paramters():
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


def test_load_json():
    datamock = {
        'host': 'publichost',
        'client_port':  5252,
        'server_port': 2525,
        'server_out_port': 6952,
        'family': socket.AF_ALG.value,
        'connection_timeout': 59,
        'database_path': '/some/fake/path',
        'database_purge': 1,
        'database_in_memory': 1,
        'cert_path': '/another/fake/path'
    }
    m = mock_open(read_data=json.dumps(datamock))

    with patch("pyjabber.server_parameters.open", m):
        param = Parameters().from_json("fake.json")

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
