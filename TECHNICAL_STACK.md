# Technical Stack — Secure Device Provisioning Pipeline

This guide describes the technologies, libraries, and patterns used in the Secure Device Provisioning Pipeline for engineers and integrators.

---

## 1. Runtime & Language

| Component | Choice | Notes |
|-----------|--------|--------|
| **Language** | Python 3.10+ | Used for CA scripts, server, client, and tests. |
| **Package management** | `pip` + `requirements.txt` | Optional: use a virtual environment (e.g. `python3 -m venv .venv`). |

**Why Python:** Strong support for cryptography (PKI, TLS), fast iteration for factory tooling, and broad deployment familiarity. The same codebase can be adapted for embedded or different runtimes later.

---

## 2. Cryptography & PKI

| Component | Technology | Role |
|-----------|------------|------|
| **Library** | [cryptography](https://cryptography.io/) | Key generation, X.509 certs/CSRs, signing, PEM serialization. |
| **Curve** | **secp256r1** (NIST P-256) | Used for Root CA, Factory CA, bootstrap cert, server cert, and device keys. |
| **Signature algorithm** | **ECDSA with SHA-256** | All certificate signatures. |
| **Certificate format** | X.509 (PEM) | Interoperable with OpenSSL and typical TLS stacks. |

**PKI hierarchy:**

- **Root CA:** Long-lived, self-signed; used only to sign the Factory CA. Stored in `ca/root_ca/`.
- **Factory CA:** Intermediate; signs device certificates, bootstrap certificates, and (in this setup) the server certificate. Stored in `ca/factory_ca/`.
- **Leaf certs:** Bootstrap (client auth), server (server auth), and device (client auth). Device cert subject includes `device:<VIN>` in the Common Name.

**Key storage:** CA and server private keys are written with restricted permissions (e.g. `chmod 400`); the script handles existing read-only files when re-running CA setup.

---

## 3. Server Stack

| Component | Technology | Role |
|-----------|------------|------|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) | REST API, request validation (Pydantic), async-capable. |
| **ASGI server** | [Uvicorn](https://www.uvicorn.org/) | Serves the FastAPI app over TLS with configurable client certificate verification. |
| **TLS** | Python `ssl` (via Uvicorn) | Server certificate + **client certificate required** (`ssl.CERT_REQUIRED`). |

**TLS configuration (Uvicorn):**

- `--ssl-keyfile` / `--ssl-certfile`: Server identity (signed by Factory CA).
- `--ssl-cert-reqs 2`: Require client certificate (2 = `CERT_REQUIRED`).
- `--ssl-ca-certs`: Path to Root CA; used to verify client certs (bootstrap certs chain Root → Factory → bootstrap).

**API:**

- `POST /provision`: Body `{"vin": "<string>"}`. Returns `{"private_key_pem", "device_cert_pem"}` over the already-established mTLS connection.
- `GET /health`: Liveness check.

**Security behavior:** Unauthenticated clients (no cert or invalid cert) are rejected at the TLS handshake; they never reach the application layer.

---

## 4. Client Stack

| Component | Technology | Role |
|-----------|------------|------|
| **HTTP client** | [requests](https://requests.readthedocs.io/) | HTTPS with client certificate and server verification. |
| **TLS** | Same as server | Client presents bootstrap cert; verifies server using Root CA. |

**Usage:** `client/device_client.py` is a CLI that:

- Loads bootstrap cert and key from configurable paths (default: `certs/bootstrap/`).
- Verifies the server with `ca/root_ca/ca.crt`.
- POSTs `{"vin": "..."}` to `https://<host>:<port>/provision`.
- Writes returned `private_key_pem` and `device_cert_pem` to the enclave directory (e.g. `certs/device_enclave/<vin>.key`, `<vin>.crt`) and sets **chmod 400** to simulate a secure enclave.

---

## 5. Audit & Persistence

| Component | Technology | Role |
|-----------|------------|------|
| **Database** | SQLite 3 | Single-file, server-local audit log. |
| **Schema** | Two tables | `provisioning_success` (VIN, timestamp_utc, certificate_serial), `provisioning_failure` (timestamp_utc, reason, optional client_identity). |
| **Access** | `sqlite3` stdlib | Used from `server/audit.py`; no ORM. |

**When logged:**

- **Success:** After generating and signing the device cert, before sending the response (VIN, UTC timestamp, device certificate serial number).
- **Failure:** On invalid request (e.g. missing/empty VIN). Failed mTLS handshakes do not reach the app and are not logged in the DB (could be added via reverse proxy or custom TLS layer if required).

The DB file (`provisioning_audit.db`) lives in the server directory; in Docker, a volume can be mounted for persistence.

---

## 6. Containerization

| Component | Technology | Role |
|-----------|------------|------|
| **Runtime** | Docker | Build and run the factory server in a container. |
| **Base image** | `python:3.12-slim` | Minimal Python 3.12 image. |
| **Build** | Multi-step Dockerfile | Install dependencies, copy `ca/`, run `ca/scripts/setup_ca.py` (generates Root, Factory CA, server cert, bootstrap cert), copy `server/`, then run Uvicorn with mTLS flags. |

**Deployment notes:**

- CA and server certs are generated at **build time** for a self-contained image; for production, consider mounting CA and certs from a vault.
- **Volume:** Mount a volume for the server directory (or a dedicated path) to persist `provisioning_audit.db`.
- **Port:** Container exposes 8443 (HTTPS).

---

## 7. Testing

| Layer | Tool | Scope |
|-------|------|--------|
| **Runner** | [pytest](https://pytest.org/) | All tests under `tests/`. |
| **Crypto** | `tests/test_crypto.py` | Certificate chain validation: Root self-signed, Factory signed by Root, device cert signed by Factory, bootstrap signed by Factory. Uses `cryptography` to load and verify certs. |
| **mTLS negative** | `tests/test_mtls_negative.py` | Starts server in subprocess; asserts no-client-cert is rejected (SSLError) and valid bootstrap cert is accepted (200 + JSON with key/cert). May skip if server does not start in time. |
| **Injection** | `tests/test_injection.py` | Loads key/cert from enclave (or uses in-memory key/cert if none) and verifies ECDSA sign/verify. |

**Running tests:** From project root, with dependencies installed:

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

---

## 8. Project Layout (Technical)

```
device-provission/
├── ca/
│   ├── root_ca/           # Root CA key and cert (vault)
│   ├── factory_ca/        # Factory CA key and cert (vault)
│   └── scripts/
│       └── setup_ca.py     # Generates full PKI + bootstrap + server certs
├── server/
│   ├── factory_server.py   # FastAPI app: /provision, /health, key gen, signing, audit
│   ├── audit.py            # SQLite schema and log_success / log_failure
│   └── Dockerfile          # Container build and run
├── client/
│   └── device_client.py   # CLI: POST /provision, write to enclave (chmod 400)
├── certs/
│   ├── bootstrap/         # Bootstrap client cert and key (output of setup_ca)
│   ├── server/             # Server TLS cert and key
│   └── device_enclave/     # Per-VIN device key and cert (client output)
├── tests/
│   ├── conftest.py        # PYTHONPATH and _require_ca fixture
│   ├── test_crypto.py     # Chain validation
│   ├── test_mtls_negative.py # mTLS rejection / acceptance
│   └── test_injection.py  # Sign/verify with injected key
├── requirements.txt
├── README.md
├── PRESENTATION.md        # Stakeholder presentation
└── TECHNICAL_STACK.md    # This document
```

---

## 9. Configuration & Deployment Summary

| Concern | How it's handled |
|---------|-------------------|
| **CA and cert paths** | Defaults derived from project root (`Path(__file__).resolve().parent`); overridable via env or CLI where applicable. |
| **Server TLS** | Uvicorn CLI args: `--ssl-keyfile`, `--ssl-certfile`, `--ssl-cert-reqs 2`, `--ssl-ca-certs`. |
| **Client** | CLI args: `--url`, `--bootstrap-key`, `--bootstrap-crt`, `--root-ca`, `--enclave-dir`. |
| **Audit DB path** | Default: `server/provisioning_audit.db`; can be overridden in `audit.py` (e.g. via env). |
| **Secrets** | Keys and certs are file-based; in production, use a proper secrets manager or HSM and restrict filesystem permissions. |

---

## 10. References

- **Architecture & planning:** `ARCHITECTURE_PROVISIONING.md`, `PLANNING_PROVISIONING.md`
- **Quick start:** `README.md`
- **Stakeholder overview:** `PRESENTATION.md`
- **Libraries:** [cryptography](https://cryptography.io/), [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [requests](https://requests.readthedocs.io/), [pytest](https://pytest.org/)

---

*Document: TECHNICAL_STACK.md — Secure Device Provisioning Pipeline*
