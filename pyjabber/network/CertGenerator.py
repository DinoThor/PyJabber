import os
from loguru import logger

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime


def check_hostname_cert_exists(host: str, cert_path: os.path):
    previous_path = os.getcwd()
    try:
        os.chdir(cert_path)

        res = True
        for file in [f"{host}_key.pem", f"{host}_csr.pem", f"{host}_cert.pem"]:
            if os.path.isfile(file) is False:
                logger.debug("Missing hostname certificate")
                res = False

        os.chdir(os.path.join(previous_path))
        return res

    except FileNotFoundError:
        logger.warning("Bad format from cert path. Check it")
        return False


def generate_hostname_cert(host: str, cert_path: os.path):
    logger.debug("Generating hostname certificate")
    previous_path = os.getcwd()

    os.chdir(cert_path)

    for file in [f"{host}_key.pem", f"{host}_csr.pem", f"{host}_cert.pem"]:
        if os.path.isfile(file):
            os.remove(file)

    domain_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    with open(f"{host}_key.pem", "wb") as f:
        f.write(domain_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    domain_name = host
    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Spade"),
        x509.NameAttribute(NameOID.COMMON_NAME, domain_name),
    ])).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(domain_name)]),
        critical=False,
    ).sign(domain_key, hashes.SHA256(), default_backend())

    with open(f"{host}_csr.pem", "wb") as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))

    with open("ca_key.pem", "rb") as f:
        ca_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    with open("ca_cert.pem", "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

    domain_cert = x509.CertificateBuilder().subject_name(
        csr.subject
    ).issuer_name(
        ca_cert.subject
    ).public_key(
        csr.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365 * 10)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(domain_name)]),
        critical=False,
    ).sign(ca_key, hashes.SHA256(), default_backend())

    with open(f"{host}_cert.pem", "wb") as f:
        f.write(domain_cert.public_bytes(serialization.Encoding.PEM))

    os.chdir(previous_path)

    logger.debug(f"Certificate generated for => {host}")
