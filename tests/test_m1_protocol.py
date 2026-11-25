"""Unit tests for Module 1: Foundation and Protocol."""
import pytest
from pydantic import ValidationError

from shared.config import (
    DB_PATH,
    HEARTBEAT_INTERVAL,
    HEARTBEAT_TIMEOUT,
    HOST,
    MAX_TASK_ATTEMPTS,
    PORT,
)
from shared.protocol import (
    GpuInfo,
    HeartbeatMsg,
    RegisterMsg,
    ResultMsg,
    TaskMsg,
    parse_message,
)


def test_config_heartbeat_timeout_greater_than_interval():
    """Verify that HEARTBEAT_TIMEOUT is strictly greater than HEARTBEAT_INTERVAL."""
    assert HEARTBEAT_TIMEOUT > HEARTBEAT_INTERVAL
    assert HOST == "0.0.0.0"
    assert PORT == 8000
    assert MAX_TASK_ATTEMPTS == 3
    assert DB_PATH == "omnicompute.db"


def test_register_msg_json_roundtrip():
    """Verify RegisterMsg converts to JSON and back with matching values (with GPU)."""
    msg = RegisterMsg(
        worker_id="worker-01",
        hostname="node-gpu.local",
        cpu_cores=16,
        ram_gb=32.0,
        gpu=GpuInfo(name="NVIDIA RTX 4090", vram_gb=24.0),
    )
    json_str = msg.model_dump_json()
    parsed = parse_message(json_str)

    assert isinstance(parsed, RegisterMsg)
    assert parsed.worker_id == "worker-01"
    assert parsed.hostname == "node-gpu.local"
    assert parsed.cpu_cores == 16
    assert parsed.ram_gb == 32.0
    assert parsed.gpu is not None
    assert parsed.gpu.name == "NVIDIA RTX 4090"
    assert parsed.gpu.vram_gb == 24.0
    assert parsed == msg


def test_register_msg_accepts_gpu_none():
    """Verify gpu=None is valid for CPU-only workers."""
    msg = RegisterMsg(
        worker_id="worker-cpu-01",
        hostname="node-cpu.local",
        cpu_cores=8,
        ram_gb=16.0,
        gpu=None,
    )
    json_str = msg.model_dump_json()
    parsed = parse_message(json_str)

    assert isinstance(parsed, RegisterMsg)
    assert parsed.gpu is None
    assert parsed.worker_id == "worker-cpu-01"
    assert parsed == msg


def test_heartbeat_msg_json_roundtrip():
    """Verify HeartbeatMsg converts to JSON and back with matching values."""
    msg = HeartbeatMsg(
        worker_id="worker-01",
        cpu_percent=45.5,
        ram_percent=60.2,
        gpu_percent=78.0,
        running_tasks=2,
    )
    json_str = msg.model_dump_json()
    parsed = parse_message(json_str)

    assert isinstance(parsed, HeartbeatMsg)
    assert parsed.worker_id == "worker-01"
    assert parsed.cpu_percent == 45.5
    assert parsed.ram_percent == 60.2
    assert parsed.gpu_percent == 78.0
    assert parsed.running_tasks == 2
    assert parsed == msg


def test_task_msg_json_roundtrip():
    """Verify TaskMsg converts to JSON and back with matching values."""
    msg = TaskMsg(
        task_id="task-101",
        job_id="job-999",
        task_type="monte_carlo_pi",
        payload={"samples": 500000, "seed": 1234},
    )
    json_str = msg.model_dump_json()
    parsed = parse_message(json_str)

    assert isinstance(parsed, TaskMsg)
    assert parsed.task_id == "task-101"
    assert parsed.job_id == "job-999"
    assert parsed.task_type == "monte_carlo_pi"
    assert parsed.payload == {"samples": 500000, "seed": 1234}
    assert parsed == msg


def test_result_msg_json_roundtrip():
    """Verify ResultMsg converts to JSON and back with matching values."""
    msg = ResultMsg(
        task_id="task-101",
        status="ok",
        output={"hits": 392700, "samples": 500000},
        duration_ms=45.2,
    )
    json_str = msg.model_dump_json()
    parsed = parse_message(json_str)

    assert isinstance(parsed, ResultMsg)
    assert parsed.task_id == "task-101"
    assert parsed.status == "ok"
    assert parsed.output == {"hits": 392700, "samples": 500000}
    assert parsed.duration_ms == 45.2
    assert parsed == msg


def test_missing_required_field_raises_validation_error():
    """Verify omitting required fields raises a ValidationError."""
    with pytest.raises(ValidationError):
        # Missing cpu_cores and ram_gb
        RegisterMsg(worker_id="w-01", hostname="node")

    with pytest.raises(ValidationError):
        # Missing worker_id, cpu_percent, ram_percent
        HeartbeatMsg()

    with pytest.raises(ValidationError):
        # Missing task_id, job_id
        TaskMsg()

    with pytest.raises(ValidationError):
        # Missing task_id
        ResultMsg()


def test_wrong_type_raises_validation_error():
    """Verify passing invalid types (e.g. string for int) raises an error."""
    with pytest.raises(ValidationError):
        RegisterMsg(
            worker_id="w-01",
            hostname="node",
            cpu_cores="abc",  # type: ignore[arg-type]
            ram_gb=16.0,
        )

    with pytest.raises(ValidationError):
        HeartbeatMsg(
            worker_id="w-01",
            cpu_percent="invalid",  # type: ignore[arg-type]
            ram_percent=50.0,
        )


def test_parse_message_rejects_unknown_type():
    """Verify parse_message raises ValueError for unknown message types."""
    with pytest.raises(ValueError, match="Unknown message type"):
        parse_message('{"type": "nonexistent_action", "data": 123}')


def test_parse_message_rejects_broken_json():
    """Verify parse_message raises ValueError for malformed JSON text."""
    with pytest.raises(ValueError, match="Invalid JSON message"):
        parse_message('{"type": "register", incomplete json...')

    with pytest.raises(ValueError, match="JSON object"):
        parse_message("[1, 2, 3]")


def test_parse_message_rejects_missing_type_field():
    """Verify parse_message raises ValueError if 'type' key is omitted."""
    with pytest.raises(ValueError, match="Missing 'type' field"):
        parse_message('{"worker_id": "w-01", "hostname": "node"}')

