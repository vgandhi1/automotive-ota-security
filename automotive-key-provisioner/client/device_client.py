"""
Device client: connects with bootstrap cert (mTLS), requests identity, stores in Secure Enclave.
Phases 2–3: POST /provision with VIN, save private_key_pem and device_cert_pem with chmod 400.
"""
import argparse
import os
import sys
from pathlib import Path

import requests

# Project root for default paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_BOOTSTRAP_KEY = PROJECT_ROOT / "certs" / "bootstrap" / "bootstrap.key"
DEFAULT_BOOTSTRAP_CRT = PROJECT_ROOT / "certs" / "bootstrap" / "bootstrap.crt"
DEFAULT_ROOT_CA = PROJECT_ROOT / "ca" / "root_ca" / "ca.crt"
DEFAULT_ENCLAVE_DIR = PROJECT_ROOT / "certs" / "device_enclave"


def provision(
    vin: str,
    base_url: str,
    bootstrap_key: Path = DEFAULT_BOOTSTRAP_KEY,
    bootstrap_crt: Path = DEFAULT_BOOTSTRAP_CRT,
    root_ca: Path = DEFAULT_ROOT_CA,
    enclave_dir: Path = DEFAULT_ENCLAVE_DIR,
) -> None:
    """Request device identity from factory server and store in enclave (chmod 400)."""
    if not vin or not vin.strip():
        print("error: vin is required and must be non-empty", file=sys.stderr)
        sys.exit(1)
    vin = vin.strip()

    url = f"{base_url.rstrip('/')}/provision"
    try:
        r = requests.post(
            url,
            json={"vin": vin},
            cert=(str(bootstrap_crt), str(bootstrap_key)),
            verify=str(root_ca),
            timeout=30,
        )
        r.raise_for_status()
    except requests.exceptions.SSLError as e:
        print(f"error: mTLS failed: {e}", file=sys.stderr)
        sys.exit(2)
    except requests.exceptions.RequestException as e:
        print(f"error: request failed: {e}", file=sys.stderr)
        sys.exit(3)

    data = r.json()
    private_key_pem = data.get("private_key_pem")
    device_cert_pem = data.get("device_cert_pem")
    if not private_key_pem or not device_cert_pem:
        print("error: invalid response missing key or cert", file=sys.stderr)
        sys.exit(4)

    enclave_dir.mkdir(parents=True, exist_ok=True)
    # One set per VIN so multiple provisions don't overwrite
    key_path = enclave_dir / f"{vin}.key"
    cert_path = enclave_dir / f"{vin}.crt"

    key_path.write_text(private_key_pem)
    cert_path.write_text(device_cert_pem)
    os.chmod(key_path, 0o400)
    os.chmod(cert_path, 0o400)

    print(f"Stored device identity in {enclave_dir} (chmod 400): {vin}.key, {vin}.crt")


def main():
    parser = argparse.ArgumentParser(description="Device provisioning client (mTLS)")
    parser.add_argument("vin", help="Vehicle Identification Number")
    parser.add_argument(
        "--url",
        default="https://localhost:8443",
        help="Factory server base URL (default: https://localhost:8443)",
    )
    parser.add_argument("--bootstrap-key", type=Path, default=DEFAULT_BOOTSTRAP_KEY)
    parser.add_argument("--bootstrap-crt", type=Path, default=DEFAULT_BOOTSTRAP_CRT)
    parser.add_argument("--root-ca", type=Path, default=DEFAULT_ROOT_CA)
    parser.add_argument("--enclave-dir", type=Path, default=DEFAULT_ENCLAVE_DIR)
    args = parser.parse_args()

    provision(
        vin=args.vin,
        base_url=args.url,
        bootstrap_key=args.bootstrap_key,
        bootstrap_crt=args.bootstrap_crt,
        root_ca=args.root_ca,
        enclave_dir=args.enclave_dir,
    )


if __name__ == "__main__":
    main()
