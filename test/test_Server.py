from unittest.mock import patch

import pytest

from pyjabber.server import Server
from pyjabber.server_parameters import Parameters


@pytest.fixture
def setup():
    with patch('pyjabber.server.logger') as mock_log, \
         patch('pyjabber.server.DB') as mock_db, \
         patch('pyjabber.server.init_utils') as mock_utils:
        mock_utils.setup_query_local_ip.return_value = '127.0.0.1'
        mock_utils.setup_ip_by_host.return_value =
        param = Parameters()
        yield Server(param), mock_log, mock_db


def test_exit_exception():
    with pytest.raises(SystemExit):
        Server.raise_exit()


def test_run_server(setup):
    server, log, db = setup

    assert log.call_args_list == ["Starting server...", "Client domain => localhost"]
