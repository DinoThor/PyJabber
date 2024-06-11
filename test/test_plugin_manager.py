import pytest
from unittest.mock import MagicMock
from xml.etree.ElementTree import Element
from pyjabber.plugins.PluginManager import PluginManager
from pyjabber.plugins.roster.Roster import Roster
from pyjabber.plugins.xep_0199.xep_0199 import Ping
from pyjabber.stanzas.error import StanzaError as SE

def test_plugin_manager_initialization():
    manager = PluginManager("example@domain.com")
    assert 'jabber:iq:roster' in manager._plugins
    assert 'urn:xmpp:ping' in manager._plugins
    assert isinstance(manager._plugins['jabber:iq:roster'], type)
    assert isinstance(manager._plugins['urn:xmpp:ping'], type)


def test_feed_with_known_plugin():
    manager = PluginManager("example@domain.com")
    manager._activePlugins = {
        'jabber:iq:roster': MagicMock(spec=Roster),
        'urn:xmpp:ping': MagicMock(spec=Ping)
    }

    # Crear un elemento de prueba para el plugin Roster
    element = Element('iq', {'type': 'get'})
    subelement = Element('{jabber:iq:roster}query')
    element.append(subelement)

    manager.feed(element)
    assert manager._activePlugins['jabber:iq:roster'].feed.called


def test_feed_with_unknown_plugin():
    manager = PluginManager("example@domain.com")
    # Crear un elemento de prueba para un plugin no registrado
    element = Element('iq', {'type': 'get'})
    subelement = Element('{jabber:iq:unknown}query')
    element.append(subelement)

    result = manager.feed(element)
    assert result == SE.service_unavaliable()


def test_feed_with_no_child():
    manager = PluginManager("example@domain.com")
    element = Element('iq', {'type': 'result'})

    # No debería llamar a ningún plugin ni lanzar excepciones
    result = manager.feed(element)
    assert result is None


def test_feed_with_error_handling():
    manager = PluginManager("example@domain.com")
    manager._plugins = {
        'jabber:iq:roster': MagicMock(Roster)
    }
    # Simular que el plugin necesario no está activo ni disponible
    element = Element('iq', {'type': 'get'})
    subelement = Element('{urn:xmpp:ping}ping')
    element.append(subelement)

    result = manager.feed(element)
    assert result == SE.service_unavaliable()
    assert 'urn:xmpp:ping' not in manager._activePlugins

