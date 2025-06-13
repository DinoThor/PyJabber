from xml.etree import ElementTree as ET

from pyjabber.features.SASLFeature import MECHANISM, SASL
from pyjabber.stream.Signal import Signal
from pyjabber.stream.StreamHandler import StreamHandler, Stage


class StreamServerIncomingHandler(StreamHandler):
    def __init__(self, transport, starttls, parser_ref) -> None:
        super().__init__(transport, starttls, parser_ref)
        self._ibr_feature = False
        self._sasl_mechanisms = [MECHANISM.EXTERNAL]

        self._stages_handlers[Stage.AUTH] = self._handle_empty_features
        self._stages_handlers.pop(Stage.BIND)

    def _handle_empty_features(self, _):
        self._streamFeature.reset()
        self._transport.write(self._streamFeature.to_bytes())

        self._stage = Stage.READY
        return Signal.DONE

