"""Shared fixtures: starts a dedicated test server on port 8001."""
import json
import subprocess
import time
from pathlib import Path

import pytest
import requests

PROJECT_ROOT = Path(__file__).parent.parent
CUSTOM_FILE = PROJECT_ROOT / "taxonomy_custom.json"
BASE_URL = "http://localhost:8001"
API_KEY = "aaa"


@pytest.fixture(scope="session", autouse=True)
def server():
    """Start a fresh uvicorn process on port 8001 for the test session."""
    saved = CUSTOM_FILE.read_text() if CUSTOM_FILE.exists() else None
    CUSTOM_FILE.write_text('{"additions": [], "edits": {}}')

    proc = subprocess.Popen(
        [str(PROJECT_ROOT / ".venv/bin/uvicorn"), "main:app", "--port", "8001"],
        cwd=PROJECT_ROOT,
    )
    for _ in range(30):
        try:
            requests.get(f"{BASE_URL}/", timeout=1)
            break
        except requests.ConnectionError:
            time.sleep(0.3)
    else:
        proc.terminate()
        raise RuntimeError("Test server did not start in time.")

    yield

    proc.terminate()
    proc.wait()
    if saved is not None:
        CUSTOM_FILE.write_text(saved)
    else:
        CUSTOM_FILE.write_text('{"additions": [], "edits": {}}')


@pytest.fixture()
def restore_custom():
    """Restore taxonomy_custom.json after a write test."""
    before = CUSTOM_FILE.read_text()
    yield
    CUSTOM_FILE.write_text(before)
