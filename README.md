# Secure Device Provisioning Pipeline

Factory Provisioning Server and device client for secure key injection over mTLS, as specified in `ARCHITECTURE_PROVISIONING.md` and `PLANNING_PROVISIONING.md`.

- **PRESENTATION.md** — Stakeholder-style presentation (problem, solution, architecture, value, demo).
- **TECHNICAL_STACK.md** — Technical stack guide (languages, libraries, PKI, server/client, audit, Docker, tests).

## Quick start

1. **Create Python env** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
   On Debian/Ubuntu if `venv` fails: `sudo apt install python3.12-venv`.

2. **Generate CA and certs** (run once):
   ```bash
   python3 ca/scripts/setup_ca.py
   ```
   This creates Root CA, Factory CA, server cert, and bootstrap client cert under `ca/` and `certs/`.

3. **Start the server** (mTLS on port 8443):
   ```bash
   python3 -m uvicorn server.factory_server:app --host 0.0.0.0 --port 8443 \
     --ssl-keyfile certs/server/server.key --ssl-certfile certs/server/server.crt \
     --ssl-cert-reqs 2 --ssl-ca-certs ca/root_ca/ca.crt
   ```

4. **Provision a device** (from another terminal):
   ```bash
   python3 -m client.device_client VIN12345 --url https://localhost:8443
   ```
   Device identity is written to `certs/device_enclave/VIN12345.key` and `VIN12345.crt` with `chmod 400`.

## Tests

From project root with `PYTHONPATH=.`:

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

- **test_crypto.py**: Certificate chain validation (Root → Factory → device/bootstrap).
- **test_mtls_negative.py**: No client cert is rejected; valid bootstrap cert is accepted (starts server in subprocess; may skip if server does not start in time).
- **test_injection.py**: Injected key can sign a message and verify with the device cert.

## Docker

Build and run the server in a container (build from project root):

```bash
docker build -f server/Dockerfile -t factory-provisioning .
docker run -p 8443:8443 -v provisioning_audit_data:/app/server factory-provisioning
```

Use the host’s CA and bootstrap certs for the client, or copy `certs/bootstrap` and `ca/root_ca/ca.crt` from the image for testing.

## Layout

- `ca/scripts/setup_ca.py` — Root CA, Factory CA, server cert, bootstrap cert.
- `server/factory_server.py` — mTLS provisioning API; `server/audit.py` — SQLite audit log; `server/Dockerfile`.
- `client/device_client.py` — Device client (bootstrap cert, POST /provision, save to enclave).
- `tests/` — Crypto, mTLS negative, and injection verification tests.
