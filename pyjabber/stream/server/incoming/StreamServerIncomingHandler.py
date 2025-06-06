from xml.etree import ElementTree as ET

from pyjabber.features.SASLFeature import MECHANISM
from pyjabber.stream.StreamHandler import StreamHandler, Stage

try:
    from typing import override
except ImportError:
    def override(func): return func


class StreamServerIncomingHandler(StreamHandler):
    def __init__(self, transport, starttls, parser_ref) -> None:
        super().__init__(transport, starttls, parser_ref)
        self._ibr_feature = False
        self._sasl_mechanisms = [MECHANISM.EXTERNAL]

        self._stages_handlers = {
            Stage.AUTH: self._handle_empty_feautres,
        }
        self._stages_handlers.pop(Stage.BIND)

    def _handle_empty_feautres(self, element: ET.Element):
        self._streamFeature.reset()
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.READY

