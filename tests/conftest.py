"""Shared test fixtures for OmniCompute test suites."""
import os
import socket
import tempfile
import pytest


@pytest.fixture
def free_port() -> int:
    """Find and return an unused local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database file and clean it up after test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass

