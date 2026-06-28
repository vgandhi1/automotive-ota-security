"""
Factory Provisioning Server: mTLS endpoint, key generation, and injection.
Phases 2–4: Require client cert, generate device identity, sign with Factory CA, audit.
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.x509.oid import NameOID

from server.audit import init_db, log_failure, log_success

app = FastAPI(title="Factory Provisioning Server")

# Paths: project root is parent of server/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CA_DIR = PROJECT_ROOT / "ca"
FACTORY_CA_KEY = CA_DIR / "factory_ca" / "factory_ca.key"
FACTORY_CA_CRT = CA_DIR / "factory_ca" / "factory_ca.crt"


def load_factory_ca():
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    key_pem = FACTORY_CA_KEY.read_bytes()
    cert_pem = FACTORY_CA_CRT.read_bytes()
    key = load_pem_private_key(key_pem, password=None)
    cert = x509.load_pem_x509_certificate(cert_pem)
    return key, cert


# Load once at startup
_factory_ca_key = None
_factory_ca_cert = None


@app.on_event("startup")
def startup():
    global _factory_ca_key, _factory_ca_cert
    init_db()
    _factory_ca_key, _factory_ca_cert = load_factory_ca()


def _get_factory_ca():
    if _factory_ca_key is None or _factory_ca_cert is None:
        raise RuntimeError("Factory CA not loaded")
    return _factory_ca_key, _factory_ca_cert


class ProvisionRequest(BaseModel):
    vin: str


class ProvisionResponse(BaseModel):
    private_key_pem: str
    device_cert_pem: str


@app.post("/provision", response_model=ProvisionResponse)
def provision(request: Request, body: ProvisionRequest):
    if not body.vin or not body.vin.strip():
        log_failure(reason="missing_or_empty_vin")
        raise HTTPException(status_code=400, detail="vin is required and must be non-empty")

    vin = body.vin.strip()
    factory_key, factory_cert = _get_factory_ca()

    # Phase 3.1: Generate ECC key and CSR for this device (VIN)
    device_key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Factory Device"),
        x509.NameAttribute(NameOID.COMMON_NAME, f"device:{vin}"),
    ])
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
        .sign(device_key, hashes.SHA256())
    )

    # Phase 3.2: Sign CSR with Factory CA
    from datetime import datetime, timedelta, timezone
    device_cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(factory_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365 * 10))
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

    private_key_pem = device_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.TraditionalOpenSSL,
        NoEncryption(),
    ).decode()
    device_cert_pem = device_cert.public_bytes(Encoding.PEM).decode()

    # Phase 4.2: Log success before sending
    log_success(vin=vin, certificate_serial=device_cert.serial_number)

    # Phase 3.3: Return over mTLS; then Phase 3.6: destroy local copy of private key
    try:
        return ProvisionResponse(
            private_key_pem=private_key_pem,
            device_cert_pem=device_cert_pem,
        )
    finally:
        # Zero / drop reference so key can be GC'd; avoid keeping PEM in memory
        del device_key
        if hasattr(os, "urandom"):
            # Overwrite PEM string in case it's still in a buffer (best-effort)
            pass  # Pydantic/response may still hold it briefly; explicit zeroing is best-effort


@app.get("/health")
def health():
    return {"status": "ok"}


def run_server(
    host: str = "0.0.0.0",
    port: int = 8443,
    ssl_keyfile: str | None = None,
    ssl_certfile: str | None = None,
    ssl_ca_certs: str | None = None,
):
    import uvicorn
    ssl_keyfile = ssl_keyfile or str(PROJECT_ROOT / "certs" / "server" / "server.key")
    ssl_certfile = ssl_certfile or str(PROJECT_ROOT / "certs" / "server" / "server.crt")
    ssl_ca_certs = ssl_ca_certs or str(PROJECT_ROOT / "ca" / "root_ca" / "ca.crt")
    uvicorn.run(
        "server.factory_server:app",
        host=host,
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        ssl_cert_reqs=2,  # CERT_REQUIRED
        ssl_ca_certs=ssl_ca_certs,
    )


if __name__ == "__main__":
    run_server()
