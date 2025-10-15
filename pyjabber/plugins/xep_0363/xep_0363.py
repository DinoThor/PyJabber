import xml.etree.ElementTree as ET
from uuid import uuid4

from pyjabber import metadata
from pyjabber.plugins.xep_0363.upload_server import UploadHttpServer
from pyjabber.stanzas.IQ import IQ
from pyjabber.stream.JID import JID
from pyjabber.utils import Singleton
from pyjabber.stanzas.error import StanzaError as SE

class HTTPFieldUpload(metaclass=Singleton):
    __slots__ = ('_host', '_max_size', '_http_app_instance')

    def __init__(self, http_app_instance: UploadHttpServer):
        self._host = "upload.$".replace("$", metadata.HOST)
        self._max_size = metadata.ITEMS["upload.$"]["extra"]["max-size"]
        self._http_app_instance: UploadHttpServer = http_app_instance

    def feed(self, jid: JID, element: ET.Element):
        if len(element) != 1:
            return SE.invalid_xml()

        request = element.find('{urn:xmpp:http:upload:0}request')
        if request is None:
            return SE.invalid_xml()

        filename = request.attrib.get('filename')
        size = request.attrib.get('size')

        try:
            size = int(size)
        except TypeError:
            return SE.not_acceptable("Missing \"size\" parameter")
        except ValueError:
            return SE.not_acceptable("Invalid \"size\" parameter. Must be an integer")

        content_type = request.attrib.get('content-type')

        if size > self._max_size:
            return SE.not_acceptable(f"File too large. The maximum file size is {self._max_size} bytes")

        slot_id = self._http_app_instance.slot_request(filename=filename, content_type=content_type, content_length=size)
        iq_res = IQ(
            type_=IQ.TYPE.RESULT,
            from_=metadata.HOST,
            to=str(jid),
            id_=element.attrib.get('id') or str(uuid4())
        )

        slot = ET.SubElement(iq_res, '{urn:xmpp:http:upload:0}slot')
        ET.SubElement(slot, '{urn:xmpp:http:upload:0}put', attrib={
            "url": f"http://{metadata.HOST}:9090/upload/{slot_id}/{filename}"
        })
        ET.SubElement(slot, '{urn:xmpp:http:upload:0}get', attrib={
            "url": f"http://{metadata.HOST}:9090/upload/{slot_id}/{filename}"
        })

        return ET.tostring(iq_res)


