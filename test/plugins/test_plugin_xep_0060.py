from unittest.mock import patch
from uuid import uuid4
from xml.etree import ElementTree as ET

import pytest

from pyjabber.plugins.xep_0060.xep_0060 import success_response
from pyjabber.stanzas.IQ import IQ

# @pytest.fixture
# def pubsub():
#     with patch('pyjabber.plugins.xep_0060.xep_0060.host') as mock_host, \
#          patch('pyjabber.plugins.xep_0060.xep_0060.config_path') as mock_config_path, \
#          patch('pyjabber.plugins.xep_0060.xep_0060.ConnectionManager') as mock_connection, \
#          patch('pyjabber.plugins.xep_0060.xep_0060.update_memory_from_database') as mock_updater, \



def test_success_response():
    payload = ET.Element('test', attrib={'id': str(uuid4())})

    with patch('pyjabber.plugins.xep_0060.xep_0060.host') as mock_host:
        mock_host.get.return_value = 'pubsub.demo'
        iq_res, pubsub_res = success_response(payload)
        iq_res_own, pubsub_res_own = success_response(payload, True)

    assert iq_res.tag == 'iq'
    assert iq_res.attrib.get('type') == IQ.TYPE.RESULT.value
    assert iq_res.attrib.get('id') == payload.attrib.get('id')

    assert iq_res_own.tag == 'iq'
    assert iq_res_own.attrib.get('type') == IQ.TYPE.RESULT.value
    assert iq_res_own.attrib.get('id') == payload.attrib.get('id')

    assert pubsub_res.tag == '{http://jabber.org/protocol/pubsub}pubsub'
    assert pubsub_res_own.tag == '{http://jabber.org/protocol/pubsub#owner}pubsub'
