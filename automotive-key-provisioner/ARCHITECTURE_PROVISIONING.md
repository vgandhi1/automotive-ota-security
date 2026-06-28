# Architecture: Secure Device Provisioning Pipeline

## 1. High-Level Design
The system relies on a localized Public Key Infrastructure (PKI) to establish trust on the factory floor. The Factory Server acts as both a secure communications endpoint and an automated Certificate Authority (CA) for the newly manufactured vehicles.



The architecture ensures that sensitive cryptographic keys are never transmitted in plaintext over the factory network.

## 2. Mutual TLS (mTLS) Handshake Sequence
Standard TLS only authenticates the server to the client. In a zero-trust factory environment, we use mTLS so the server also verifies the device is a legitimate factory product before sending its permanent identity.



* **Client Hello:** Device initiates a connection to the Factory Server.
* **Server Hello + Cert Request:** Server responds and demands the device's factory-installed bootstrap certificate.
* **Client Cert + Key Exchange:** Device sends its bootstrap certificate to prove it is a genuine hardware unit.
* **Verification:** Server validates the bootstrap certificate against the Root CA.
* **Secure Tunnel Established:** An AES-GCM encrypted tunnel is created for the payload transfer.

---

## 3. Cryptographic Data Flow

| Step | Component | Action | Security Mechanism |
| :--- | :--- | :--- | :--- |
| **1** | `Device Client` | Connects to Server | mTLS via Bootstrap Certificate |
| **2** | `Factory Server`| Generates Keypair | `secp256r1` (NIST P-256) Elliptic Curve |
| **3** | `Factory Server`| Signs Certificate | SHA-256 with ECDSA |
| **4** | `Factory Server`| Transmits Identity | Encrypted via TLS 1.3 |
| **5** | `Device Client` | Stores Identity | Linux `chmod 400` (Simulating Secure Enclave) |
| **6** | `Factory Server`| Destroys Local Copy| Explicit memory deletion/zeroing |

---

## 4. Threat Model & Mitigations

| Threat | Description | Mitigation Strategy |
| :--- | :--- | :--- |
| **Network Sniffing** | Attacker monitors factory network to steal device keys. | Keys are transmitted exclusively over a mutually authenticated TLS 1.3 encrypted tunnel. |
| **Rogue Device** | Attacker plugs a laptop into the factory network to request keys. | Server actively drops connections that lack a valid hardware bootstrap certificate. |
| **Insider Threat** | Employee attempts to copy keys directly from the provisioning server. | The server deletes the private key from RAM immediately after transmission. Audit logs track all certificate issuances. |