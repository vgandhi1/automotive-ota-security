#!/usr/bin/env python3
"""
Phase 1: Certificate Authority (CA) Setup.
Creates Root CA, Intermediate Factory CA, and CA vault layout.
Optionally generates a manufacturing bootstrap certificate for device clients.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.x509.oid import NameOID

# Vault layout: run from project root or set DEVICE_PROVISIONING_ROOT
SCRIPT_DIR = Path(__file__).resolve().parent
CA_BASE = SCRIPT_DIR.parent
ROOT_CA_DIR = CA_BASE / "root_ca"
FACTORY_CA_DIR = CA_BASE / "factory_ca"

# Validity
ROOT_CA_DAYS = 3650  # 10 years
FACTORY_CA_DAYS = 1825  # 5 years
BOOTSTRAP_DAYS = 365  # 1 year


def ensure_vault_dirs():
    """Task 1.3: Create CA vault directory structure with restricted permissions."""
    for d in (ROOT_CA_DIR, FACTORY_CA_DIR):
        d.mkdir(parents=True, exist_ok=True)
        # Restrict to owner only (simulating locked-down factory server)
        os.chmod(d, 0o700)


def generate_root_ca():
    """Task 1.1: Generate Root CA private key and self-signed certificate."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Factory Root CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Factory Root CA"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=ROOT_CA_DAYS))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=1),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert


def generate_factory_ca(root_key, root_cert):
    """Task 1.2: Generate Intermediate Factory CA signed by Root CA."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Factory CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Factory Intermediate CA"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(root_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=FACTORY_CA_DAYS))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    return key, cert


def generate_bootstrap_cert(factory_key, factory_cert, out_bootstrap_dir: Path):
    """Generate manufacturing bootstrap certificate signed by Factory CA."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Factory Device Bootstrap"),
        x509.NameAttribute(NameOID.COMMON_NAME, "bootstrap.factory.local"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(factory_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=BOOTSTRAP_DAYS))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(factory_key, hashes.SHA256())
    )
    out_bootstrap_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_key_path = out_bootstrap_dir / "bootstrap.key"
    if bootstrap_key_path.exists():
        os.chmod(bootstrap_key_path, 0o600)
    bootstrap_key_path.write_text(
        key.private_bytes(
            Encoding.PEM,
            PrivateFormat.TraditionalOpenSSL,
            NoEncryption(),
        ).decode(),
    )
    os.chmod(out_bootstrap_dir / "bootstrap.key", 0o400)
    (out_bootstrap_dir / "bootstrap.crt").write_text(
        cert.public_bytes(Encoding.PEM).decode(),
    )
    os.chmod(out_bootstrap_dir / "bootstrap.key", 0o400)
    return key, cert


def generate_server_cert(factory_key, factory_cert, out_server_dir: Path):
    """Generate TLS server certificate signed by Factory CA (for factory_server)."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Factory Server"),
        x509.NameAttribute(NameOID.COMMON_NAME, "factory.server.local"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(factory_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("factory.server.local"),
            ]),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(factory_key, hashes.SHA256())
    )
    out_server_dir.mkdir(parents=True, exist_ok=True)
    server_key_path = out_server_dir / "server.key"
    if server_key_path.exists():
        os.chmod(server_key_path, 0o600)
    server_key_path.write_bytes(
        key.private_bytes(
            Encoding.PEM,
            PrivateFormat.TraditionalOpenSSL,
            NoEncryption(),
        )
    )
    os.chmod(out_server_dir / "server.key", 0o400)
    (out_server_dir / "server.crt").write_bytes(cert.public_bytes(Encoding.PEM))
    return key, cert


def write_ca_files(root_key, root_cert, factory_key, factory_cert):
    """Write CA keys and certs to vault with restricted permissions."""
    def safe_write(path: Path, data: bytes, key_file: bool = False):
        if path.exists():
            os.chmod(path, 0o600)
        path.write_bytes(data)
        if key_file:
            os.chmod(path, 0o400)

    safe_write(ROOT_CA_DIR / "ca.key", root_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.TraditionalOpenSSL,
        NoEncryption(),
    ), key_file=True)
    (ROOT_CA_DIR / "ca.crt").write_bytes(root_cert.public_bytes(Encoding.PEM))

    safe_write(FACTORY_CA_DIR / "factory_ca.key", factory_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.TraditionalOpenSSL,
        NoEncryption(),
    ), key_file=True)
    (FACTORY_CA_DIR / "factory_ca.crt").write_bytes(
        factory_cert.public_bytes(Encoding.PEM)
    )


def main():
    # Resolve project root for certs/bootstrap (optional)
    project_root = CA_BASE.parent
    bootstrap_dir = project_root / "certs" / "bootstrap"
    server_certs_dir = project_root / "certs" / "server"

    ensure_vault_dirs()
    root_key, root_cert = generate_root_ca()
    factory_key, factory_cert = generate_factory_ca(root_key, root_cert)
    write_ca_files(root_key, root_cert, factory_key, factory_cert)
    generate_bootstrap_cert(factory_key, factory_cert, bootstrap_dir)
    generate_server_cert(factory_key, factory_cert, server_certs_dir)

    print("CA vault created:")
    print(f"  {ROOT_CA_DIR}/ca.key, ca.crt")
    print(f"  {FACTORY_CA_DIR}/factory_ca.key, factory_ca.crt")
    print(f"  Bootstrap cert: {bootstrap_dir}/bootstrap.key, bootstrap.crt")
    print(f"  Server cert: {server_certs_dir}/server.key, server.crt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
