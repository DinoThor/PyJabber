import pytest
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element, SubElement
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.xep_0199.xep_0199 import Ping
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.JID import JID

@pytest.fixture
def setup():
    with patch('pyjabber.plugins.PluginManager.Disco'), \
         patch('pyjabber.plugins.PluginManager.PubSub'), \
         patch('pyjabber.plugins.PluginManager.Roster'), \
         patch('pyjabber.plugins.PluginManager.Ping'):

        yield PluginManager(JID("example@domain.com"))

def test_plugin_manager_initialization(setup):
    manager = setup
    assert 'jabber:iq:roster' in manager._plugins
    assert 'urn:xmpp:ping' in manager._plugins
    assert isinstance(manager._plugins['jabber:iq:roster'], object)
    assert isinstance(manager._plugins['urn:xmpp:ping'], object)


def test_feed_with_known_plugin(setup):
    manager = setup
    element = Element('iq', {'type': 'set'})
    SubElement(element, '{urn:xmpp:ping}ping')

    manager.feed(element)

    assert manager._plugins['urn:xmpp:ping'].feed.called


def test_feed_with_unknown_plugin(setup):
    manager = setup

    element = Element('iq', {'type': 'get'})
    SubElement(element, '{jabber:iq:unknown}query')
    result = manager.feed(element)
    assert result == SE.feature_not_implemented('query', 'jabber:iq:unknown')


def test_feed_with_no_child(setup):
    manager = setup

    # Crear un elemento de prueba para el plugin Roster
    element = Element('iq', {'type': 'result'})

    # No debería llamar a ningún plugin ni lanzar excepciones
    result = manager.feed(element)
    assert result is None
