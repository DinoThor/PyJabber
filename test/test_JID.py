from uuid import uuid4
import pytest

from pyjabber.stream.JID import JID


def test_standard_jid():
    jid = JID(jid='demotest@host')

    assert jid.user == 'demotest'
    assert jid.domain == 'host'
    assert jid.resource is None


def test_user_and_domain_jid():
    jid = JID(user='demotest', domain='host')

    assert jid.user == 'demotest'
    assert jid.domain == 'host'
    assert jid.resource is None


def test_user_and_domain_and_resource_jid():
    resource = str(uuid4())
    jid = JID(user='demotest', domain='host', resource=resource)

    assert jid.user == 'demotest'
    assert jid.domain == 'host'
    assert jid.resource == resource


def test_to_string_jid():
    jid_string = f'demo@host/{str(uuid4())}'
    jid = JID(jid_string)

    assert jid_string == str(jid)


def test_bad_arguments():
    with pytest.raises(ValueError):
        JID(jid='demo@host', user='demo')
    with pytest.raises(ValueError):
        JID(jid='demo@host', domain='demo')
    with pytest.raises(ValueError):
        JID(jid='demo@host', resource='demo')
    with pytest.raises(ValueError):
        JID(jid='demo')
