"""Unit tests for Module 3: Worker registration and registry persistence."""
import time
import pytest
from fastapi.testclient import TestClient

from coordinator.db import get_worker, list_workers
from coordinator.main import create_app
from shared.protocol import GpuInfo, RegisterMsg


def test_fake_worker_register_persists_in_database(tmp_db):
    """Verify worker registration creates a row with status='alive' in workers table."""
    app = create_app(tmp_db)
    client = TestClient(app)

    reg_msg = RegisterMsg(
        worker_id="test-worker-alpha",
        hostname="alpha-node.cluster",
        cpu_cores=8,
        ram_gb=16.0,
        gpu=GpuInfo(name="NVIDIA RTX 3080", vram_gb=10.0),
    )

    with client.websocket_connect("/ws/worker") as ws:
        ws.send_text(reg_msg.model_dump_json())

        # Wait briefly for the server async loop to process and write to SQLite
        worker = None
        for _ in range(50):
            worker = get_worker(tmp_db, "test-worker-alpha")
            if worker is not None and app.state.registry.is_connected("test-worker-alpha"):
                break
            time.sleep(0.02)

        # Check DB row while socket is active
        assert worker is not None
        assert worker["id"] == "test-worker-alpha"
        assert worker["hostname"] == "alpha-node.cluster"
        assert worker["cpu_cores"] == 8
        assert worker["ram_gb"] == 16.0
        assert worker["gpu_name"] == "NVIDIA RTX 3080"
        assert worker["vram_gb"] == 10.0
        assert worker["status"] == "alive"

        # Check in-memory registry contains active socket
        assert app.state.registry.is_connected("test-worker-alpha")

    # After websocket closes, in-memory registry removes worker
    assert not app.state.registry.is_connected("test-worker-alpha")


def test_duplicate_registration_creates_single_row(tmp_db):
    """Verify that registering the same worker_id multiple times updates the existing row."""
    app = create_app(tmp_db)
    client = TestClient(app)

    reg1 = RegisterMsg(
        worker_id="reused-worker-id",
        hostname="node-1.cluster",
        cpu_cores=4,
        ram_gb=8.0,
        gpu=None,
    )
    reg2 = RegisterMsg(
        worker_id="reused-worker-id",
        hostname="node-1-renamed.cluster",
        cpu_cores=4,
        ram_gb=8.0,
        gpu=None,
    )

    with client.websocket_connect("/ws/worker") as ws:
        ws.send_text(reg1.model_dump_json())
        ws.send_text(reg2.model_dump_json())

    workers = list_workers(tmp_db)
    assert len(workers) == 1
    assert workers[0]["id"] == "reused-worker-id"
    assert workers[0]["hostname"] == "node-1-renamed.cluster"
