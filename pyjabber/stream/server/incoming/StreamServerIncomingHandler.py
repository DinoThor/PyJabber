from pyjabber.features.SASL.Mechanism import MECHANISM
from pyjabber.stream.utils.Enums import Signal
from pyjabber.stream.negotiators.StreamNegotiator import Stage, StreamNegotiator


class StreamServerIncomingHandler(StreamNegotiator):
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

