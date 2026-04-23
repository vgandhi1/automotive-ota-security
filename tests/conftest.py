# Pytest: run from project root with PYTHONPATH=. so that server and client packages are importable.
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


@pytest.fixture(scope="module")
def _require_ca():
    ca_root = root / "ca" / "root_ca" / "ca.crt"
    factory_crt = root / "ca" / "factory_ca" / "factory_ca.crt"
    if not ca_root.exists() or not factory_crt.exists():
        pytest.skip("CA not set up (run python3 ca/scripts/setup_ca.py)")
