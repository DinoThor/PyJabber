from unittest.mock import patch, MagicMock
from uuid import uuid4
from xml.etree import ElementTree as ET

import pytest
from sqlalchemy import create_engine, insert, delete, select, and_

from pyjabber.db.model import Model
from pyjabber.plugins.xep_0060.xep_0060 import PubSub
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton


@pytest.fixture(scope='function')
def setup_database():
    engine = create_engine("sqlite:///:memory:")
    Model.server_metadata.create_all(engine)
    query = insert(Model.Pubsub).values([
        {
            "node": "TestNode",
            "owner": "demo",
            "name": "Sample",
            "type": "leaf",
            "max_items": 1024
        }, {
            "node": "TestNode2",
            "owner": "test",
            "name": "Sample",
            "type": "leaf",
            "max_items": 1024
        }
    ])
    query2 = insert(Model.PubsubSubscribers).values([
        {
            "node": "TestNode",
            "jid": "test",
            "subid": "123456789",
            "subscription": "subscribed",
            "affiliation": "publisher"
        }, {
            "node": "TestNode",
            "jid": "dump",
            "subid": "123321123321",
            "subscription": "pending",
            "affiliation": "none"
        }, {
            "node": "TestNode",
            "jid": "unsub",
            "subid": "123321",
            "subscription": "pending",
            "affiliation": "none"
        }, {
            "node": "TestNode",
            "jid": "unsub",
            "subid": "123322",
            "subscription": "pending",
            "affiliation": "none"
        }
    ])
    query3 = insert(Model.PubsubItems).values([
        {
            "node": "TestNode",
            "publisher": "demo",
            "item_id": "123",
            "payload": '<message from="juliet@example.com/balcony" id="ktx72v49" to="romeo@example.net" type="chat" xml:lang="en"><body>Art thou not Romeo, and a Montague?</body></message>'
        }, {
            "node": "TestNode",
            "publisher": "demo",
            "item_id": "124",
            "payload": '<message from="juliet@example.com/balcony" id="ktx72v50" to="romeo@example.net" type="chat" xml:lang="en"><body>Neither, fair saint, if either thee dislike.</body></message>'
        },
    ])
    con = engine.connect()
    con.execute(query)
    con.execute(query2)
    con.execute(query3)
    con.commit()

    yield engine

    con.close()


@pytest.fixture(scope='function')
def pubsub(setup_database):
    with patch('pyjabber.plugins.xep_0060.xep_0060.metadata') as mock_meta, \
         patch('pyjabber.plugins.xep_0060.xep_0060.ConnectionManager') as mock_connection, \
         patch('pyjabber.plugins.xep_0060.xep_0060.DB') as mock_db:
        Singleton._instances = {}

        engine = setup_database
        mock_db.connection = lambda: engine.connect()
        mock_meta.HOST = 'localhost'
        mock_meta.ITEMS = {
            'pubsub.$': {
                "name": "Pubsub Service",
                "category": "pubsub",
                "type": "service",
                "var": "http://jabber.org/protocol/pubsub"
            }
        }
        pubsub = PubSub()
        yield pubsub, engine


def test_success_response():
    payload = ET.Element('test', attrib={'id': str(uuid4())})

    with patch('pyjabber.plugins.xep_0060.xep_0060.metadata') as mock_meta:
        mock_meta.HOST = 'pubsub.demo'
        iq_res, pubsub_res = PubSub.success_response(payload)
        iq_res_own, pubsub_res_own = PubSub.success_response(payload, True)

    assert iq_res.tag == 'iq'
    assert iq_res.attrib.get('type') == IQ.TYPE.RESULT.value
    assert iq_res.attrib.get('id') == payload.attrib.get('id')

    assert iq_res_own.tag == 'iq'
    assert iq_res_own.attrib.get('type') == IQ.TYPE.RESULT.value
    assert iq_res_own.attrib.get('id') == payload.attrib.get('id')

    assert pubsub_res.tag == '{http://jabber.org/protocol/pubsub}pubsub'
    assert pubsub_res_own.tag == '{http://jabber.org/protocol/pubsub#owner}pubsub'


def test_update_memory_from_database(pubsub):
    pubsub, _ = pubsub
    pubsub._nodes = []
    pubsub._subscribers = []
    pubsub.update_memory_from_database()

    assert len(pubsub._nodes) > 0
    assert len(pubsub._subscribers) > 0

    assert pubsub._nodes == [
        ('TestNode', 'demo', 'Sample', 'leaf', 1024), ('TestNode2', 'test', 'Sample', 'leaf', 1024)
    ]
    assert pubsub._subscribers == [
        ('TestNode', 'test', '123456789', 'subscribed', 'publisher'),
        ("TestNode", "dump", "123321123321", "pending", "none"),
        ('TestNode', 'unsub', '123321', 'pending', 'none'),
        ("TestNode", "unsub", "123322", "pending", "none")
    ]


def test_feed(pubsub):
    pubsub, _ = pubsub
    mock_operation = MagicMock()
    pubsub._operations = {
        'create': mock_operation
    }

    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='create1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><create node='testNode'/></pubsub></iq>"
    )
    jid = JID("test@localhost")
    with patch('pyjabber.plugins.xep_0060.xep_0060.StanzaError') as mock_se:
        pubsub.feed(jid, element)
        mock_operation.assert_called_with(element, jid)
        mock_se.invalid_xml.assert_not_called()


def test_feed_invalid(pubsub):
    pubsub, _ = pubsub
    mock_operation = MagicMock()
    pubsub._operations = {
        'create': mock_operation
    }

    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='create1'><subpub xmlns='http://jabber.org/protocol/pubsub'><create node='testNode'/></subpub></iq>"
    )
    jid = JID("test@localhost")
    with patch('pyjabber.plugins.xep_0060.xep_0060.StanzaError') as mock_se:
        pubsub.feed(jid, element)
        mock_operation.assert_not_called()
        mock_se.invalid_xml.assert_called()


def test_feed_exception(pubsub):
    pubsub, _ = pubsub
    mock_operation = MagicMock()
    pubsub._operations = {
        'create': mock_operation
    }

    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='create1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><plunge node='testNode'/></pubsub></iq>"
    )
    jid = JID("test@localhost")
    with patch('pyjabber.plugins.xep_0060.xep_0060.StanzaError') as mock_se, \
         patch('pyjabber.plugins.xep_0060.xep_0060.logger') as mock_log:
        pubsub.feed(jid, element)
        mock_log.error.assert_called()
        mock_operation.assert_not_called()
        mock_se.feature_not_implemented.assert_called()


def test_discovery_items(pubsub):
    pubsub, _ = pubsub
    res = pubsub.discover_items()
    assert res == [('TestNode', 'Sample', 'leaf'), ('TestNode2', 'Sample', 'leaf')]


def test_discover_info(pubsub):
    pubsub, _ = pubsub
    res = pubsub.discover_info('TestNode')
    assert res == ("Sample", "leaf")


def test_create_node(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='test@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><create node='TestNode3'/></pubsub></iq>"
    )
    jid = JID("test@localhost")
    res = pubsub.create_node(element, jid)

    assert ('TestNode3', 'test', None, 'leaf', 1024) in pubsub._nodes
    assert res == b'<iq xmlns:ns0="http://jabber.org/protocol/pubsub" id="items1" from="localhost" type="result"><ns0:pubsub><create node="TestNode3" /></ns0:pubsub></iq>'


def test_create_node_no_node(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='test@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><create/></pubsub></iq>"
    )
    jid = JID("test@localhost")
    res = pubsub.create_node(element, jid)

    assert ('TestNode3', 'test', None, 'leaf', 1024) not in pubsub._nodes
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="items1" to="test@localhost" type="error"><error type="auth"><ns0:not-acceptable /><ns1:nodeid-required /></error></iq>'


def test_create_node_conflict(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='test@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><create node='TestNode'/></pubsub></iq>"
    )
    jid = JID("test@localhost")
    res = pubsub.create_node(element, jid)

    assert len(pubsub._nodes) == 2
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="items1" to="test@localhost" type="error"><error type="auth"><ns0:conflict /></error></iq>'


def test_delete_node(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='demo@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub#owner'><delete node='TestNode'/></pubsub></iq>"
    )
    jid = JID("demo@localhost")
    res = pubsub.delete_node(element, jid)

    assert len(pubsub._nodes) == 1
    assert ('TestNode', 'test', None, 'leaf', 1024) not in pubsub._nodes
    assert res == b'<iq xmlns:ns0="http://jabber.org/protocol/pubsub" id="items1" from="localhost" type="result"><ns0:pubsub /></iq>'


def test_delete_node_no_node(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='demo@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub#owner'><delete/></pubsub></iq>"
    )
    jid = JID("demo@localhost")
    res = pubsub.delete_node(element, jid)

    assert len(pubsub._nodes) == 2
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="items1" to="demo@localhost" type="error"><error type="auth"><ns0:not-acceptable /><ns1:nodeid-required /></error></iq>'


def test_delete_node_not_found(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='demo@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub#owner'><delete node='TestNode3'/></pubsub></iq>"
    )
    jid = JID("demo@localhost")
    res = pubsub.delete_node(element, jid)

    assert len(pubsub._nodes) == 2
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="items1" to="demo@localhost" type="error"><error type="cancel"><ns0:item-not-found /></error></iq>'


def test_delete_node_forbidden(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='test@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub#owner'><delete node='TestNode'/></pubsub></iq>"
    )
    jid = JID("test@localhost")
    res = pubsub.delete_node(element, jid)

    assert len(pubsub._nodes) == 2
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="items1" to="test@localhost" type="error"><error type="auth"><ns0:forbidden /></error></iq>'


def test_retrieve_items_node(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='demo@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><items node='TestNode'/></pubsub></iq>"
    )
    jid = JID("demo@localhost")
    res = pubsub.retrieve_items_node(element, jid)
    res = ET.fromstring(res)
    try:
        first, second = res[0][0][0][0][0], res[0][0][1][0][0]
    except IndexError:
        pytest.fail()

    assert first.text == 'Art thou not Romeo, and a Montague?'
    assert second.text == 'Neither, fair saint, if either thee dislike.'


def test_retrieve_items_node_forbidden(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='fake@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><items node='TestNode'/></pubsub></iq>"
    )
    jid = JID("fake@localhost")
    res = pubsub.retrieve_items_node(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="items1" to="fake@localhost" type="error"><error type="auth"><ns0:forbidden /></error></iq>'


def test_retrieve_items_node_not_found(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='fake@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><items node='NodeTest'/></pubsub></iq>"
    )
    jid = JID("fake@localhost")
    res = pubsub.retrieve_items_node(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="items1" to="fake@localhost" type="error"><error type="cancel"><ns0:item-not-found /></error></iq>'


def test_retrieve_items_node_no_node(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='fake@localhost' to='pubsub.localhost' id='items1'><pubsub xmlns='http://jabber.org/protocol/pubsub'><items/></pubsub></iq>"
    )
    jid = JID("fake@localhost")
    res = pubsub.retrieve_items_node(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="items1" to="fake@localhost" type="error"><error type="auth"><ns0:not-acceptable /><ns1:nodeid-required /></error></iq>'


def test_subscribe(pubsub):
    pubsub, engine = pubsub
    with patch('pyjabber.plugins.xep_0060.xep_0060.uuid4') as mock_uuid:
        mock_uuid.return_value = '987654321'
        element = ET.fromstring(
            "<iq type='set' from='fake@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscribe node='TestNode' jid='fake@localhost'/></pubsub></iq>"
        )
        jid = JID("fake@localhost")
        res = pubsub.subscribe(element, jid)

        assert any(s == ('TestNode', 'fake', '987654321', 'subscribed', 'publisher') for s in pubsub._subscribers)
        with engine.connect() as con:
            query = select(Model.PubsubSubscribers).where(
                and_(
                    Model.PubsubSubscribers.c.node == 'TestNode',
                    Model.PubsubSubscribers.c.jid == 'fake'
                )
            )
            res_query = con.execute(query).fetchall()
        assert len(res_query) == 1
        res_query = res_query.pop()
        assert all(prop in res_query for prop in ['TestNode', 'fake', '987654321', 'subscribed', 'publisher'])
        assert res == b'<iq xmlns:ns0="http://jabber.org/protocol/pubsub" id="sub" from="localhost" type="result"><ns0:pubsub><subscription node="TestNode" jid="fake@localhost" subid="987654321" subscription="subscribed" /></ns0:pubsub></iq>'


def test_subscribe_no_node(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='fake@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscribe jid='fake@localhost'/></pubsub></iq>"
    )
    jid = JID("fake@localhost")
    res = pubsub.subscribe(element, jid)

    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="fake@localhost" type="error"><error type="auth"><ns0:not-acceptable /><ns1:nodeid-required /></error></iq>'


def test_subscribe_no_jid(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='fake@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscribe node='TestNode'/></pubsub></iq>"
    )
    jid = JID("fake@localhost")
    res = pubsub.subscribe(element, jid)

    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="fake@localhost" type="error"><error type="modify"><ns0:bad-request /><ns1:invalid-jid /></error></iq>'


def test_subscribe_jid_inconsistent(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='fake@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscribe node='TestNode' jid='unfake@localhost'/></pubsub></iq>"
    )
    jid = JID("fake@localhost")
    res = pubsub.subscribe(element, jid)

    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="fake@localhost" type="error"><error type="modify"><ns0:bad-request /><ns1:invalid-jid /></error></iq>'


def test_subscribe_not_found(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='fake@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscribe node='NodeTest' jid='fake@localhost'/></pubsub></iq>"
    )
    jid = JID("fake@localhost")
    res = pubsub.subscribe(element, jid)

    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="sub" to="fake@localhost" type="error"><error type="cancel"><ns0:item-not-found /></error></iq>'


def test_subscribe_subscribed_already(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscribe node='TestNode' jid='test@localhost'/></pubsub></iq>"
    )
    jid = JID("test@localhost")
    res = pubsub.subscribe(element, jid)

    assert res == b'<iq xmlns:ns0="http://jabber.org/protocol/pubsub" id="sub" from="localhost" type="result"><ns0:pubsub><subscription node="TestNode" jid="test@localhost" subid="123456789" subscription="subscribed" /></ns0:pubsub></iq>'


def test_subscribe_subscribed_pending(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='dump@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscribe node='TestNode' jid='dump@localhost'/></pubsub></iq>"
    )
    jid = JID("dump@localhost")
    res = pubsub.subscribe(element, jid)

    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="dump@localhost" type="error"><error type="auth"><ns0:not-authorized /><ns1:pending-subscription /></error></iq>'


def test_unsubscribe(pubsub):
    pubsub, engine = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe node='TestNode' jid='test@localhost'/></pubsub></iq>"
    )
    jid = JID("test@localhost")

    assert ('TestNode', 'test', '123456789', 'subscribed', 'publisher') in pubsub._subscribers

    res = pubsub.unsubscribe(element, jid)

    assert ('TestNode', 'test', '123456789', 'subscribed', 'publisher') not in pubsub._subscribers
    with engine.connect() as con:
        query = select(Model.PubsubSubscribers)
        res_query = con.execute(query).fetchall()
    assert ('TestNode', 'test', '123456789', 'subscribed', 'publisher') not in res_query
    assert res == b'<iq xmlns:ns0="http://jabber.org/protocol/pubsub" id="sub" from="localhost" type="result"><ns0:pubsub><subscription node="TestNode" jid="test@localhost" subscription="none" /></ns0:pubsub></iq>'


def test_unsubscribe_no_node(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe jid='test@localhost'/></pubsub></iq>"
    )
    jid = JID("test@localhost")

    res = pubsub.unsubscribe(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="test@localhost" type="error"><error type="auth"><ns0:not-acceptable /><ns1:nodeid-required /></error></iq>'


def test_unsubscribe_no_jid(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe node='TestNode'/></pubsub></iq>"
    )
    jid = JID("test@localhost")

    res = pubsub.unsubscribe(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="test@localhost" type="error"><error type="modify"><ns0:bad-request /><ns1:invalid-jid /></error></iq>'


def test_unsubscribe_invalid_jid(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe node='TestNode' jid='test@localhost'/></pubsub></iq>"
    )
    jid = JID("tset@localhost")

    res = pubsub.unsubscribe(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="tset@localhost" type="error"><error type="modify"><ns0:bad-request /><ns1:invalid-jid /></error></iq>'


def test_unsubscribe_item_not_found(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe node='TestNode6' jid='test@localhost'/></pubsub></iq>"
    )
    jid = JID("test@localhost")

    res = pubsub.unsubscribe(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="sub" to="test@localhost" type="error"><error type="cancel"><ns0:item-not-found /></error></iq>'


def test_unsubscribe_not_subscribed(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='dummy@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe node='TestNode' jid='dummy@localhost'/></pubsub></iq>"
    )
    jid = JID("dummy@localhost")

    res = pubsub.unsubscribe(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="dummy@localhost" type="error"><error type="cancel"><ns0:unexpected-request /><ns1:not-subscribed /></error></iq>'


def test_unsubscribe_need_subid(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='unsub@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe node='TestNode' jid='unsub@localhost'/></pubsub></iq>"
    )
    jid = JID("unsub@localhost")

    res = pubsub.unsubscribe(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="unsub@localhost" type="error"><error type="modify"><ns0:bad-request /><ns1:subid-required /></error></iq>'


def test_unsubscribe_invalid_subid(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='unsub@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe node='TestNode' jid='unsub@localhost' subid='123320'/></pubsub></iq>")
    jid = JID("unsub@localhost")

    res = pubsub.unsubscribe(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="unsub@localhost" type="error"><error type="modify"><ns0:not-acceptable /><ns1:invalid-subid /></error></iq>'


def test_unsubscribe_with_subid(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><unsubscribe node='TestNode' jid='test@localhost'/></pubsub></iq>")
    jid = JID("test@localhost")

    res = pubsub.unsubscribe(element, jid)
    assert res == b'<iq xmlns:ns0="http://jabber.org/protocol/pubsub" id="sub" from="localhost" type="result"><ns0:pubsub><subscription node="TestNode" jid="test@localhost" subscription="none" /></ns0:pubsub></iq>'


def test_retrieve_subscriptions(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscriptions node='TestNode'/></pubsub></iq>")
    jid = JID("test@localhost")

    res = pubsub.retrieve_subscriptions(element, jid)
    assert res == b'<iq xmlns:ns0="http://jabber.org/protocol/pubsub" id="sub" from="localhost" type="result"><ns0:pubsub><ns0:subscriptions><ns0:subscription node="TestNode" jid="test@localhost" subscription="subscribed" subid="123456789" /></ns0:subscriptions></ns0:pubsub></iq>'


def test_retrieve_subscriptions_forbidden(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='mark@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscriptions node='TestNode'/></pubsub></iq>")
    jid = JID("test@localhost")

    res = pubsub.retrieve_subscriptions(element, jid)
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="sub" to="test@localhost" type="error"><error type="auth"><ns0:forbidden /></error></iq>'


def test_retrieve_subscriptions_all_nodes(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='get' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><subscriptions/></pubsub></iq>")
    jid = JID("test@localhost")

    res = pubsub.retrieve_subscriptions(element, jid)
    res_et = ET.fromstring(res)
    subs_et_atr = res_et[0][0][0].attrib
    assert subs_et_atr == {
        'node': 'TestNode',
        'jid': 'test@localhost',
        'subscription': 'subscribed',
        'subid': '123456789'
    }
    assert len(res_et[0][0]) == 1


def test_purge(pubsub):
    pubsub, engine = pubsub
    element = ET.fromstring(
        "<iq type='set' from='demo@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub#owner'><purge node='TestNode'/></pubsub></iq>")
    jid = JID("demo@localhost")

    with engine.connect() as con:
        query = select(Model.PubsubItems)
        res_query = con.execute(query).fetchall()
    assert len(res_query) == 2

    res = pubsub.purge(element, jid)
    with engine.connect() as con:
        query = select(Model.PubsubItems)
        res_query = con.execute(query).fetchall()
    assert len(res_query) == 0
    assert res == b'<iq xmlns:ns0="http://jabber.org/protocol/pubsub#owner" id="sub" from="localhost" type="result"><ns0:pubsub /></iq>'


def test_purge_not_found(pubsub):
    pubsub, engine = pubsub
    element = ET.fromstring(
        "<iq type='set' from='demo@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub#owner'><purge node='TestNode9'/></pubsub></iq>")
    jid = JID("demo@localhost")

    res = pubsub.purge(element, jid)

    with engine.connect() as con:
        query = select(Model.PubsubItems)
        assert len(con.execute(query).fetchall()) > 0
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="sub" to="demo@localhost" type="error"><error type="cancel"><ns0:item-not-found /></error></iq>'


def test_purge_not_forbidden(pubsub):
    pubsub, engine = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub#owner'><purge node='TestNode'/></pubsub></iq>")
    jid = JID("test@localhost")

    res = pubsub.purge(element, jid)

    with engine.connect() as con:
        query = select(Model.PubsubItems)
        assert len(con.execute(query).fetchall()) > 0
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="sub" to="test@localhost" type="error"><error type="auth"><ns0:forbidden /></error></iq>'


def test_retract(pubsub):
    pubsub, engine = pubsub
    element = ET.fromstring(
        "<iq type='set' from='demo@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><retract node='TestNode'><item id='123'/></retract></pubsub></iq>")
    jid = JID("demo@localhost")
    query = select(Model.PubsubItems).where(
        and_(
            Model.PubsubItems.c.item_id == '123',
            Model.PubsubItems.c.node == "TestNode"
        )
    )
    with engine.connect() as con:
        assert len(con.execute(query).fetchall()) == 1

    res = pubsub.retract(element, jid)

    with engine.connect() as con:
        assert len(con.execute(query).fetchall()) == 0
    assert res == b'<iq id="sub" from="localhost" type="result" />'


def test_retract_no_node(pubsub):
    pubsub, engine = pubsub
    element = ET.fromstring(
        "<iq type='set' from='demo@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><retract/><item id='123'/></pubsub></iq>")
    jid = JID("demo@localhost")
    query = select(Model.PubsubItems).where(
        and_(
            Model.PubsubItems.c.item_id == '123',
            Model.PubsubItems.c.node == "TestNode"
        )
    )
    with engine.connect() as con:
        assert len(con.execute(query).fetchall()) == 1

    res = pubsub.retract(element, jid)

    with engine.connect() as con:
        assert len(con.execute(query).fetchall()) == 1
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="demo@localhost" type="error"><error type="modify"><ns0:bad-request /><ns1:nodeid-required /></error></iq>'


def test_retract_no_item(pubsub):
    pubsub, engine = pubsub
    element = ET.fromstring(
        "<iq type='set' from='demo@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><retract node='TestNode'/></pubsub></iq>")
    jid = JID("demo@localhost")
    query = select(Model.PubsubItems).where(
        and_(
            Model.PubsubItems.c.item_id == '123',
            Model.PubsubItems.c.node == "TestNode"
        )
    )
    with engine.connect() as con:
        assert len(con.execute(query).fetchall()) == 1

    res = pubsub.retract(element, jid)

    with engine.connect() as con:
        assert len(con.execute(query).fetchall()) == 1
    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" xmlns:ns1="http://jabber.org/protocol/pubsub#errors" id="sub" to="demo@localhost" type="error"><error type="modify"><ns0:bad-request /><ns1:item-required /></error></iq>'


def test_retract_not_found(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='demo@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><retract node='TestNode12'><item id='123'/></retract></pubsub></iq>")
    jid = JID("demo@localhost")

    res = pubsub.retract(element, jid)

    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="sub" to="demo@localhost" type="error"><error type="cancel"><ns0:item-not-found /></error></iq>'


def test_retract_forbidden(pubsub):
    pubsub, _ = pubsub
    element = ET.fromstring(
        "<iq type='set' from='lac@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><retract node='TestNode'><item id='123'/></retract></pubsub></iq>")
    jid = JID("lac@localhost")

    res = pubsub.retract(element, jid)

    assert res == b'<iq xmlns:ns0="urn:ietf:params:xml:ns:xmpp-stanzas" id="sub" to="lac@localhost" type="error"><error type="auth"><ns0:forbidden /></error></iq>'



def test_retract_publisher(pubsub):
    pubsub, engine = pubsub
    element = ET.fromstring(
        "<iq type='set' from='test@localhost' to='pubsub.localhost' id='sub'><pubsub xmlns='http://jabber.org/protocol/pubsub'><retract node='TestNode'><item id='123'/></retract></pubsub></iq>")
    jid = JID("test@localhost")
    query = select(Model.PubsubItems).where(
        and_(
            Model.PubsubItems.c.item_id == '123',
            Model.PubsubItems.c.node == "TestNode"
        )
    )
    with engine.connect() as con:
        assert len(con.execute(query).fetchall()) == 1

    res = pubsub.retract(element, jid)

    with engine.connect() as con:
        assert len(con.execute(query).fetchall()) == 0

    assert res == b'<iq id="sub" from="localhost" type="result" />'



