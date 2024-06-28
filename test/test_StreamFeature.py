import pytest
from xml.etree import ElementTree as ET
from unittest.mock import MagicMock

from pyjabber.features.StreamFeature import  StreamFeature,NonUniqueFeature


def test_initialization():
    stream_feature = StreamFeature()
    assert stream_feature.tag == "stream:features"
    assert stream_feature.attrib == {"xmlns": "http://etherx.jabber.org/streams"}
    assert stream_feature._features == {}

def test_register_feature():
    stream_feature = StreamFeature()
    feature = ET.Element("feature1")

    stream_feature.register(feature)

    assert "feature1" in stream_feature._features
    assert stream_feature._features["feature1"] == feature

def test_register_non_unique_feature():
    stream_feature = StreamFeature()
    feature = ET.Element("feature1")

    stream_feature.register(feature)

    with pytest.raises(NonUniqueFeature):
        stream_feature.register(feature)

def test_unregister_feature():
    stream_feature = StreamFeature()
    feature = ET.Element("feature1")

    stream_feature.register(feature)
    stream_feature.unregister(feature)

    assert "feature1" not in stream_feature._features

def test_unregister_nonexistent_feature():
    stream_feature = StreamFeature()
    feature = ET.Element("feature1")

    # Attempting to unregister a feature that doesn't exist should do nothing
    stream_feature.unregister(feature)

    assert "feature1" not in stream_feature._features

def test_reset_features():
    stream_feature = StreamFeature()
    feature1 = ET.Element("feature1")
    feature2 = ET.Element("feature2")

    stream_feature.register(feature1)
    stream_feature.register(feature2)

    stream_feature.reset()

    assert stream_feature._features == {}

def test_tostring():
    stream_feature = StreamFeature()
    feature = ET.Element("feature1")
    stream_feature.register(feature)

    xml_string = stream_feature.tostring()

    assert xml_string == '<stream:features xmlns="http://etherx.jabber.org/streams"><feature1 /></stream:features>'

def test_tobytes():
    stream_feature = StreamFeature()
    feature = ET.Element("feature1")
    stream_feature.register(feature)

    xml_bytes = stream_feature.to_bytes()

    expected_bytes = b'<stream:features xmlns="http://etherx.jabber.org/streams"><feature1 /></stream:features>'
    assert xml_bytes == expected_bytes

