import pytest
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.xep_0199.xep_0199 import Ping
from pyjabber.stanzas.error import StanzaError as SE
from pyjabber.stream.JID import JID


def test_plugin_manager_initialization():
    with patch('pyjabber.plugins.PluginManager.Disco'):
        with patch('pyjabber.plugins.PluginManager.PubSub'):
            manager = PluginManager(JID("example@domain.com"))
            assert 'jabber:iq:roster' in manager._plugins
            assert 'urn:xmpp:ping' in manager._plugins
            assert isinstance(manager._plugins['jabber:iq:roster'], object)
            assert isinstance(manager._plugins['urn:xmpp:ping'], object)


def test_feed_with_known_plugin():
    with patch('pyjabber.plugins.PluginManager.Disco'):
        with patch('pyjabber.plugins.PluginManager.PubSub'):
            with patch('pyjabber.plugins.PluginManager.Ping') as mock_ping:
                manager = PluginManager(JID("example@domain.com"))

                # Crear un elemento de prueba para el plugin Roster
                element = Element('iq', {'type': 'set'})
                subelement = Element('{urn:xmpp:ping}ping')
                element.append(subelement)

                manager.feed(element)
                assert manager._plugins['urn:xmpp:ping'].feed.called


def test_feed_with_unknown_plugin():
    with patch('pyjabber.plugins.PluginManager.Disco'):
        with patch('pyjabber.plugins.PluginManager.PubSub'):
            with patch('pyjabber.plugins.PluginManager.Ping') as mock_ping:
                manager = PluginManager(JID("example@domain.com"))

                # Crear un elemento de prueba para el plugin Roster
                element = Element('iq', {'type': 'get'})
                subelement = Element('{jabber:iq:unknown}query')
                element.append(subelement)

                result = manager.feed(element)
                assert result == SE.feature_not_implemented('query', 'jabber:iq:unknown')


def test_feed_with_no_child():
    with patch('pyjabber.plugins.PluginManager.Disco'):
        with patch('pyjabber.plugins.PluginManager.PubSub'):
            with patch('pyjabber.plugins.PluginManager.Ping') as mock_ping:
                manager = PluginManager(JID("example@domain.com"))

                # Crear un elemento de prueba para el plugin Roster
                element = Element('iq', {'type': 'result'})

                # No debería llamar a ningún plugin ni lanzar excepciones
                result = manager.feed(element)
                assert result is None
