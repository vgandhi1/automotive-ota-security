# Project Plan: Secure Device Provisioning & Key Injection Pipeline

**Target Role:** Security Manufacturing Engineer
**Focus:** Cryptography, PKI, mutual TLS (mTLS), and Factory Security Automation.
**Status:** 🟡 Planned

---

## 1. Executive Summary
**Objective:**
Build a simulated "Factory Provisioning Server" that authenticates a bare-metal device on the assembly line and securely injects a unique cryptographic identity (Private Key and Client Certificate) into it.

**Business Value:**
Ensures that only authorized factory tools can provision devices and prevents cryptographic keys from being intercepted in plain text on the factory network. This forms the foundation of vehicle-to-cloud (IoT) trust, directly aligning with the JD's requirement to "integrate security requirements and controls into vehicle production."

---

## 2. Implementation Phases



### Phase 1: Certificate Authority (CA) Setup
**Goal:** Establish the root of trust for the factory.
- [ ] **Task 1.1:** Create a script to generate a Root CA private key and certificate using OpenSSL or the Python `cryptography` library.
- [ ] **Task 1.2:** Create an Intermediate "Factory CA" used specifically for signing device certificates.
- [ ] **Task 1.3:** Establish a secure local directory structure to act as the CA vault (simulating restricted factory server storage).

### Phase 2: Mutual TLS (mTLS) Infrastructure
**Goal:** Ensure the server and the device mutually authenticate before exchanging any data.
- [ ] **Task 2.1:** Build the `factory_server.py` using a Python framework (e.g., Flask, FastAPI, or raw sockets) configured to *require* client certificates.
- [ ] **Task 2.2:** Build the `device_client.py` configured with a temporary "manufacturing bootstrap" certificate.
- [ ] **Task 2.3:** Verify that unauthenticated clients (or clients with standard TLS) are actively rejected by the server.

### Phase 3: Key Generation & Injection Logic
**Goal:** Securely generate and transfer the vehicle's permanent identity.
- [ ] **Task 3.1:** **Server Side:** Upon successful mTLS connection, generate a new ECC (Elliptic Curve Cryptography) private key and a Certificate Signing Request (CSR) for the specific device VIN.
- [ ] **Task 3.2:** **Server Side:** Sign the CSR with the Factory CA to create the Device Certificate.
- [ ] **Task 3.3:** **Transfer:** Package the Private Key and Device Certificate in a JSON payload and send it over the mTLS tunnel to the client.
- [ ] **Task 3.4:** **Client Side:** Receive the payload and save it to a simulated "Secure Enclave" (e.g., a protected local file with strict `chmod 400` read/write permissions).

### Phase 4: Audit Logging & Containerization
**Goal:** Create an immutable record of provisioning for security audits and scale the environment.
- [ ] **Task 4.1:** Setup a SQLite database (`provisioning_audit.db`).
- [ ] **Task 4.2:** Log every successful key injection (VIN, Timestamp, Certificate Serial Number).
- [ ] **Task 4.3:** Log every failed attempt (e.g., failed mTLS handshake).
- [ ] **Task 4.4:** Write a `Dockerfile` for the server to demonstrate containerization skills.

---

## 3. Testing Strategy
* **Crypto Tests:** Unit tests verifying that generated certificates chain up to the Root CA correctly.
* **Negative Testing:** Attempt to connect with an expired or revoked bootstrap certificate to ensure the server drops the connection.
* **Injection Verification:** A secondary script that attempts to use the injected device key to sign a test message, proving the key is valid and usable.