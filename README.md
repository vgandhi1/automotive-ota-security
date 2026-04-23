# Automotive Key Provisioner

A factory-floor provisioning server and device client for secure vehicle identity key injection over **mutual TLS (mTLS)**. Models the PKI-based provisioning pipeline used when manufacturing connected vehicles: each device receives a unique cryptographic identity before leaving the factory, preventing rogue devices from ever obtaining valid credentials.

> **Disclaimer:** This is a proof-of-concept simulation for educational and portfolio purposes. It models real-world automotive security patterns using a local PKI rather than an HSM-backed production CA.

---

## Motivation

Every connected vehicle needs a cryptographic identity — a private key and signed certificate — to authenticate itself to cloud services, OTA update servers, and V2X infrastructure throughout its lifetime. The critical question is: **how does that identity get securely injected at the factory without being intercepted or counterfeited?**

Standard TLS authenticates the server to the client, but in a factory environment you also need to prove the device is genuine hardware — not a laptop plugged into the production line. **UNECE WP.29/R155** and **ISO/SAE 21434** require that OEMs establish secure provisioning processes with audit trails. This project implements that pipeline using mTLS, a three-tier PKI chain, and a tamper-evident SQLite audit log.

---

## Security Model

### PKI trust hierarchy

```
Root CA  (ca/root_ca/)
  └── Factory CA  (ca/factory_ca/)
        ├── Server Certificate  (certs/server/)       — authenticates the provisioning server
        ├── Bootstrap Certificate  (certs/bootstrap/) — pre-installed on device hardware
        └── Device Certificate  (certs/device_enclave/<VIN>.crt) — issued at provisioning time
```

The Root CA is the trust anchor. The Factory CA is an intermediate that signs both the server cert and all device bootstrap/identity certs. This structure allows the Root CA to remain offline while the Factory CA operates on the production line.

### Threat model

| Threat | Attack scenario | Mitigation |
|---|---|---|
| **Network sniffing** | Attacker monitors factory LAN to intercept device keys | Keys are transmitted exclusively inside a mutually authenticated TLS 1.3 encrypted tunnel |
| **Rogue device** | Attacker plugs a laptop into the factory network to request an identity | Server drops any connection without a valid hardware bootstrap certificate signed by the Factory CA |
| **Insider threat** | Employee copies keys from the provisioning server | Private key is deleted from server RAM immediately after transmission; all issuances are recorded in the audit log |

### Cryptographic choices

- **secp256r1 (NIST P-256)** — device keypair generation
- **SHA-256 with ECDSA** — certificate signing
- **TLS 1.3** — tunnel encryption (AES-GCM)
- **mTLS** — both sides present and verify certificates before any payload is exchanged

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [1. Set up Python environment](#1-set-up-python-environment)
  - [2. Generate CA and certificates](#2-generate-ca-and-certificates)
  - [3. Start the provisioning server](#3-start-the-provisioning-server)
  - [4. Provision a device](#4-provision-a-device)
- [Running Tests](#running-tests)
- [Docker](#docker)
- [Project Structure](#project-structure)
- [Related Standards](#related-standards)

---

## Prerequisites

- Python 3.10 or later
- `pip` and `venv`
- Docker (optional — for containerised server)

---

## Quick Start

### 1. Set up Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> On Debian/Ubuntu, if `venv` is missing: `sudo apt install python3.12-venv`

---

### 2. Generate CA and certificates

Run once to create the full PKI chain (Root CA, Factory CA, server cert, and bootstrap client cert):

```bash
python3 ca/scripts/setup_ca.py
```

This generates all keys and certificates under `ca/` and `certs/`. Private keys are excluded from version control via `.gitignore` — you must run this step after cloning.

---

### 3. Start the provisioning server

Starts the mTLS server on port 8443. The server requires client certificate authentication (`--ssl-cert-reqs 2`):

```bash
python3 -m uvicorn server.factory_server:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile certs/server/server.key \
  --ssl-certfile certs/server/server.crt \
  --ssl-cert-reqs 2 \
  --ssl-ca-certs ca/root_ca/ca.crt
```

---

### 4. Provision a device

From a second terminal, provision a device using its VIN as the identity:

```bash
python3 -m client.device_client VIN12345 --url https://localhost:8443
```

The device's unique identity is written to:
- `certs/device_enclave/VIN12345.key` — private key (`chmod 400`)
- `certs/device_enclave/VIN12345.crt` — signed device certificate

All provisioning events are recorded in `server/provisioning_audit.db`.

---

## Running Tests

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

| Test file | What it verifies |
|---|---|
| `test_crypto.py` | Full certificate chain validation: Root → Factory CA → device / bootstrap |
| `test_mtls_negative.py` | Connection without a client cert is rejected; valid bootstrap cert is accepted |
| `test_injection.py` | Injected device key can sign a message that verifies against the issued device certificate |

---

## Docker

Build and run the provisioning server in a container:

```bash
docker build -f server/Dockerfile -t automotive-key-provisioner .
docker run -p 8443:8443 -v provisioning_audit_data:/app/server automotive-key-provisioner
```

For client testing, use the CA and bootstrap certs generated in step 2, or copy them from the container.

---

## Project Structure

```
automotive-key-provisioner/
├── requirements.txt
├── ca/
│   ├── scripts/
│   │   └── setup_ca.py           # Generates full PKI chain (run once after clone)
│   ├── root_ca/
│   │   └── ca.crt                # Root CA certificate (trust anchor)
│   └── factory_ca/
│       └── factory_ca.crt        # Factory CA certificate
├── certs/
│   ├── server/
│   │   └── server.crt            # TLS server certificate
│   └── bootstrap/
│       └── bootstrap.crt         # Pre-installed device bootstrap certificate
├── server/
│   ├── factory_server.py         # mTLS provisioning API (FastAPI / uvicorn)
│   ├── audit.py                  # SQLite tamper-evident audit log
│   └── Dockerfile
├── client/
│   └── device_client.py          # Device client (presents bootstrap cert, receives identity)
├── tests/
│   ├── test_crypto.py            # Certificate chain validation tests
│   ├── test_mtls_negative.py     # Negative mTLS authentication tests
│   └── test_injection.py         # Key injection and verification tests
├── ARCHITECTURE_PROVISIONING.md  # Detailed system design and data flow
├── PLANNING_PROVISIONING.md      # Development phases and roadmap
├── TECHNICAL_STACK.md            # Technology choices and rationale
└── PRESENTATION.md               # Stakeholder-facing overview
```

> **Note:** All private key files (`.key`) are excluded from version control. Run `python3 ca/scripts/setup_ca.py` to regenerate them after cloning.

---

## Related Standards

- **UNECE WP.29 / R155** — UN regulation on cybersecurity management systems for road vehicles
- **ISO/SAE 21434** — Road vehicle cybersecurity engineering, including supply chain and factory security requirements
