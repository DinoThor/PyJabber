import unittest
from xml.etree import ElementTree as ET
from pyjabber.stanzas.Message import Message

def test_message_creation():
    mto = "user@domain.com"
    mfrom = "otheruser@domain.com"
    id = "12345"
    body = "Hello, this is a test message."
    mtype = "chat"
    tag = "message"

    msg = Message(mto=mto, mfrom=mfrom, id=id, body=body, mtype=mtype, tag=tag)

    # Verifica los atributos
    assert msg.attrib["to"] == mto
    assert msg.attrib["from"] == mfrom
    assert msg.attrib["id"] == id
    assert msg.attrib["type"] == mtype
    assert msg.tag == tag

    # Verifica el cuerpo del mensaje
    body_elem = msg.find("body")
    assert body_elem is not None
    assert body_elem.text == body

def test_message_creation_with_default_type():
    mto = "user@domain.com"
    mfrom = "otheruser@domain.com"
    id = "12345"
    body = "Hello, this is a test message."
    tag = "message"

    msg = Message(mto=mto, mfrom=mfrom, id=id, body=body, tag=tag)

    # Verifica los atributos
    assert msg.attrib["to"] == mto
    assert msg.attrib["from"] == mfrom
    assert msg.attrib["id"] == id
    assert msg.attrib["type"] == "chat"  # Valor por defecto
    assert msg.tag == tag

    # Verifica el cuerpo del mensaje
    body_elem = msg.find("body")
    assert body_elem is not None
    assert body_elem.text == body

def test_message_creation_with_extra_attributes():
    mto = "user@domain.com"
    mfrom = "otheruser@domain.com"
    id = "12345"
    body = "Hello, this is a test message."
    mtype = "chat"
    tag = "message"
    extra = {"lang": "en"}

    msg = Message(mto=mto, mfrom=mfrom, id=id, body=body, mtype=mtype, tag=tag, **extra)

    # Verifica los atributos
    assert msg.attrib["to"] == mto
    assert msg.attrib["from"] == mfrom
    assert msg.attrib["id"] == id
    assert msg.attrib["type"] == mtype
    assert msg.attrib["lang"] == "en"  # Extra attribute
    assert msg.tag == tag

    # Verifica el cuerpo del mensaje
    body_elem = msg.find("body")
    assert body_elem is not None
    assert body_elem.text == body


