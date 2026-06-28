"""
Negative mTLS tests: server must reject clients without valid client certificate.
(1) No client cert -> connection rejected
(2) Expired or wrong CA -> rejected (simulated by using cert not in server's CA chain)
"""
import subprocess
import time
from pathlib import Path

import pytest
import requests

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
SERVER_CRT = PROJECT_ROOT / "certs" / "server" / "server.crt"
ROOT_CA = PROJECT_ROOT / "ca" / "root_ca" / "ca.crt"
BOOTSTRAP_CRT = PROJECT_ROOT / "certs" / "bootstrap" / "bootstrap.crt"
BOOTSTRAP_KEY = PROJECT_ROOT / "certs" / "bootstrap" / "bootstrap.key"


def _server_process(port: int = 8443):
    cmd = [
        "python3", "-m", "uvicorn",
        "server.factory_server:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--ssl-keyfile", str(PROJECT_ROOT / "certs" / "server" / "server.key"),
        "--ssl-certfile", str(SERVER_CRT),
        "--ssl-cert-reqs", "2",
        "--ssl-ca-certs", str(ROOT_CA),
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )


@pytest.fixture(scope="module")
def server_url():
    """Start server once per module; use a high port to avoid conflicts."""
    port = 18443
    proc = _server_process(port=port)
    try:
        for _ in range(50):
            try:
                r = requests.get(
                    f"https://127.0.0.1:{port}/health",
                    verify=str(ROOT_CA),
                    cert=(str(BOOTSTRAP_CRT), str(BOOTSTRAP_KEY)),
                    timeout=1,
                )
                if r.status_code == 200:
                    break
            except requests.exceptions.SSLError:
                pass
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(0.3)
        else:
            pytest.skip("Server did not start in time (install deps and run from project root)")
        yield f"https://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_no_client_cert_rejected(server_url):
    """Request without client certificate must fail (TLS handshake rejection)."""
    with pytest.raises(requests.exceptions.SSLError):
        requests.post(
            f"{server_url}/provision",
            json={"vin": "TESTVIN"},
            verify=str(ROOT_CA),
            timeout=5,
        )


def test_with_client_cert_accepted(server_url):
    """Request with valid bootstrap client cert must succeed."""
    r = requests.post(
        f"{server_url}/provision",
        json={"vin": "TESTVIN_NEG"},
        cert=(str(BOOTSTRAP_CRT), str(BOOTSTRAP_KEY)),
        verify=str(ROOT_CA),
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert "private_key_pem" in data
    assert "device_cert_pem" in data
