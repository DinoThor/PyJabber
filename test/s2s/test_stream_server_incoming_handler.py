from unittest.mock import MagicMock, patch

from pyjabber.features.SASLFeature import MECHANISM
from pyjabber.stream.Signal import Signal
from pyjabber.stream.Stage import Stage
from pyjabber.stream.server.incoming.StreamServerIncomingHandler import StreamServerIncomingHandler


def test_constructor():
    mock_transport = MagicMock()
    mock_tls = MagicMock()
    mock_parser_red = MagicMock()

    with patch('pyjabber.stream.StreamHandler.metadata') as mock_meta:
        mock_meta.HOST = 'localhost'
        mock_meta.PLUGINS = ['jabber:iq:register']

        handler = StreamServerIncomingHandler(mock_transport, mock_tls, mock_parser_red)

    assert handler._ibr_feature == False
    assert handler._sasl_mechanisms == [MECHANISM.EXTERNAL]
    assert list(handler._stages_handlers.keys()) == [
        Stage.CONNECTED, Stage.OPENED, Stage.SSL, Stage.SASL, Stage.AUTH
    ]
    assert handler._handle_empty_features == handler._stages_handlers[Stage.AUTH]


def test_handler_empty_features():
    mock_transport = MagicMock()
    mock_tls = MagicMock()
    mock_parser_red = MagicMock()

    with patch('pyjabber.stream.StreamHandler.metadata') as mock_meta:
        mock_meta.HOST = 'localhost'
        mock_meta.PLUGINS = ['jabber:iq:register']

        handler = StreamServerIncomingHandler(mock_transport, mock_tls, mock_parser_red)
        handler._stage = Stage.AUTH

    handler._handle_empty_features = MagicMock()
    signal = handler.handle_open_stream(MagicMock())

    assert len(handler._streamFeature._features) == 0
    mock_transport.write.assert_called_with(b'<stream:features xmlns="http://etherx.jabber.org/streams" />')
    assert handler._stage == Stage.READY
    assert signal == Signal.DONE

