import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pyjabber.network.CertGenerator import check_hostname_cert_exists, \
    generate_hostname_cert

CERTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../pyjabber/network/certs'))


@pytest.fixture
def hostname():
    return "example.com"


def test_check_hostname_cert_exists_missing_file(hostname):
    def mock_isfile(path):
        # Simula que los archivos de certificados no existen
        return False

    with patch('os.path.isfile', side_effect=mock_isfile), \
        patch('os.chdir') as mock_chdir, \
        patch('loguru.logger.debug') as mock_logger_debug:
        result = check_hostname_cert_exists(hostname)

        mock_chdir.assert_any_call(CERTS_PATH)
        mock_chdir.assert_any_call(os.getcwd())
        mock_logger_debug.assert_called_with("Missing hostname certificate")
        assert result is False


def test_check_hostname_cert_exists_all_files_present(hostname):
    with patch('os.path.isfile', return_value=True), \
        patch('os.chdir') as mock_chdir:
        result = check_hostname_cert_exists(hostname)

        mock_chdir.assert_any_call(CERTS_PATH)
        mock_chdir.assert_any_call(os.getcwd())
        assert result is True


@pytest.mark.parametrize("file_exists", [True, False])
def test_generate_hostname_cert(hostname, file_exists):
    # Crear una clave privada real
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    # Crear una clave pública real
    public_key = private_key.public_key()

    # Crear mocks
    mock_csr = MagicMock()
    mock_ca_key = MagicMock()
    mock_ca_cert = MagicMock()
    mock_domain_cert = MagicMock()

    # Crear un objeto x509.Name para usar como subject e issuer
    subject_name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Spade"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])

    # Ajustar los retornos de los mocks para que sean del tipo esperado
    mock_csr.subject = subject_name
    mock_csr.public_key.return_value = public_key
    mock_ca_cert.subject = subject_name

    with patch('os.path.isfile', return_value=file_exists), \
        patch('os.remove') as mock_remove, \
        patch('os.chdir') as mock_chdir, \
        patch('builtins.open', mock_open()), \
        patch('cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key', return_value=private_key), \
        patch('cryptography.x509.CertificateSigningRequestBuilder.sign', return_value=mock_csr), \
        patch('cryptography.hazmat.primitives.serialization.load_pem_private_key', return_value=mock_ca_key), \
        patch('cryptography.x509.load_pem_x509_certificate', return_value=mock_ca_cert), \
        patch('cryptography.x509.CertificateBuilder.sign', return_value=mock_domain_cert), \
        patch('loguru.logger.debug') as mock_logger_debug, \
        patch('socket.gethostname', return_value=hostname):
        generate_hostname_cert(hostname)

        mock_chdir.assert_any_call(CERTS_PATH)
        mock_chdir.assert_any_call(os.getcwd())

        if file_exists:
            assert mock_remove.call_count == 3

        mock_logger_debug.assert_any_call("Generating hostname certificate")
        mock_logger_debug.assert_any_call(f"Certificate generated for => {hostname}")
