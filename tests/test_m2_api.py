"""Unit tests for Module 2: Coordinator API and WebSocket."""
import json
import pytest
from fastapi.testclient import TestClient

from coordinator.main import create_app
from shared.protocol import HeartbeatMsg, RegisterMsg


def test_health_endpoint_returns_ok(tmp_db):
    """Verify GET /health returns HTTP 200 and {'status': 'ok'}."""
    app = create_app(tmp_db)
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_websocket_worker_accepts_connection(tmp_db):
    """Verify WebSocket /ws/worker successfully accepts a connection."""
    app = create_app(tmp_db)
    client = TestClient(app)

    with client.websocket_connect("/ws/worker") as websocket:
        # Connection established without exception
        assert websocket is not None


def test_websocket_worker_handles_broken_json_and_recovers(tmp_db):
    """Verify broken JSON sends an error without crashing, and valid message follows."""
    app = create_app(tmp_db)
    client = TestClient(app)

    with client.websocket_connect("/ws/worker") as websocket:
        # 1. Send broken JSON text
        websocket.send_text("{broken json syntax...")
        resp = websocket.receive_json()
        assert "error" in resp

        # 2. Send valid registration message immediately after
        reg_msg = RegisterMsg(
            worker_id="worker-01",
            hostname="test-node",
            cpu_cores=4,
            ram_gb=8.0,
            gpu=None,
        )
        websocket.send_text(reg_msg.model_dump_json())

        # 3. Send valid heartbeat message
        hb_msg = HeartbeatMsg(
            worker_id="worker-01",
            cpu_percent=15.0,
            ram_percent=30.0,
            gpu_percent=0.0,
            running_tasks=0,
        )
        websocket.send_text(hb_msg.model_dump_json())

        # 4. Send another broken JSON message to verify connection is still responsive
        websocket.send_text('{"missing": "type_field"}')
        resp2 = websocket.receive_json()
        assert "error" in resp2

    # Verify both valid messages were received and stored in app state
    assert len(app.state.received_messages) == 2
    assert isinstance(app.state.received_messages[0], RegisterMsg)
    assert app.state.received_messages[0].worker_id == "worker-01"
    assert isinstance(app.state.received_messages[1], HeartbeatMsg)
    assert app.state.received_messages[1].cpu_percent == 15.0

