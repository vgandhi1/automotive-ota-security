"""
Crypto tests: certificate chain validation.
Verify Root CA -> Factory CA -> device cert chain and that device cert is signed by Factory CA.
"""
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

# Project root
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
CA_DIR = PROJECT_ROOT / "ca"
ROOT_CA_CRT = CA_DIR / "root_ca" / "ca.crt"
FACTORY_CA_CRT = CA_DIR / "factory_ca" / "factory_ca.crt"


def load_pem_cert(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def test_root_ca_self_signed(_require_ca):
    """Root CA cert should be self-signed (issuer == subject)."""
    root = load_pem_cert(ROOT_CA_CRT)
    assert root.subject == root.issuer
    assert root.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is True


def test_factory_ca_signed_by_root(_require_ca):
    """Factory CA cert should be signed by Root CA."""
    root = load_pem_cert(ROOT_CA_CRT)
    factory = load_pem_cert(FACTORY_CA_CRT)
    assert factory.issuer == root.subject
    # Verify signature
    root_pub = root.public_key()
    root_pub.verify(
        factory.signature,
        factory.tbs_certificate_bytes,
        ec.ECDSA(hashes.SHA256()),
    )
    assert factory.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is True


def test_device_cert_chain_to_root(_require_ca):
    """Device cert (signed by Factory CA) chains up to Root CA."""
    root = load_pem_cert(ROOT_CA_CRT)
    factory = load_pem_cert(FACTORY_CA_CRT)
    factory_key_path = CA_DIR / "factory_ca" / "factory_ca.key"
    if not factory_key_path.exists():
        pytest.skip("Factory CA key not found (run ca/scripts/setup_ca.py)")
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    factory_key = load_pem_private_key(factory_key_path.read_bytes(), password=None)
    device_key = ec.generate_private_key(ec.SECP256R1())
    from datetime import datetime, timedelta, timezone
    device_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "device:TESTVIN"),
        ]))
        .issuer_name(factory.subject)
        .public_key(device_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(factory_key, hashes.SHA256())
    )
    # Device cert signed by Factory CA
    factory_pub = factory.public_key()
    factory_pub.verify(
        device_cert.signature,
        device_cert.tbs_certificate_bytes,
        ec.ECDSA(hashes.SHA256()),
    )
    assert device_cert.issuer == factory.subject
    # Chain: device -> factory -> root
    assert factory.issuer == root.subject


def test_bootstrap_cert_signed_by_factory(_require_ca):
    """Bootstrap cert (if present) should be signed by Factory CA."""
    bootstrap_crt = PROJECT_ROOT / "certs" / "bootstrap" / "bootstrap.crt"
    if not bootstrap_crt.exists():
        pytest.skip("Bootstrap cert not generated (run ca/scripts/setup_ca.py)")
    factory = load_pem_cert(FACTORY_CA_CRT)
    bootstrap = load_pem_cert(bootstrap_crt)
    assert bootstrap.issuer == factory.subject
    factory_pub = factory.public_key()
    factory_pub.verify(
        bootstrap.signature,
        bootstrap.tbs_certificate_bytes,
        ec.ECDSA(hashes.SHA256()),
    )
