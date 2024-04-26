import unittest
from uuid import uuid4
import xml.etree.ElementTree as ET

from pyjabber.stanzas.Message import Message

class test_Messages(unittest.TestCase):
    def test_1(self):
        body = "demotest demotest"
        to = "demo@host"
        from_ = "test@host"
        id = str(uuid4())

        test = ET.Element(
            "message",
            attrib = {
                "from": from_,
                "to": to,
                "id": id,
                "type": "chat"
            }
        )
        bodyElem = ET.Element("body")
        bodyElem.text = body
        test.append(bodyElem)

        res = Message(body=body, mfrom=from_, id=id, mto=to)

        self.assertEqual(test.tag, res.tag)
        self.assertEqual(test.attrib, res.attrib)

    def test_2(self):
        body = "testing testing"
        to = "foo@host"
        from_ = "bar@host"
        id = str(uuid4())
        type_ = "normal"

        test = ET.Element(
            "message",
            attrib = {
                "from": from_,
                "to": to,
                "id": id,
                "type": type_
            }
        )
        bodyElem = ET.Element("body")
        bodyElem.text = body
        test.append(bodyElem)

        res = Message(body=body, mfrom=from_, id=id, mto=to, mtype=type_)

        self.assertEqual(test.tag, res.tag)
        self.assertEqual(test.attrib, res.attrib)

if __name__ == '__main__':
    unittest.main()