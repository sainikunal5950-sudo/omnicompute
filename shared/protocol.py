"""Protocol models and message serialization for OmniCompute."""
import json
from typing import Any, Dict, Literal, Optional, Union
from pydantic import BaseModel, Field, ValidationError


class GpuInfo(BaseModel):
    """Specification of a detected worker GPU."""
    name: str
    vram_gb: float


class RegisterMsg(BaseModel):
    """Worker registration message sent upon connecting to the coordinator."""
    type: Literal["register"] = "register"
    worker_id: str
    hostname: str
    cpu_cores: int
    ram_gb: float
    gpu: Optional[GpuInfo] = None


class HeartbeatMsg(BaseModel):
    """Periodic worker heartbeat message with health and load metrics."""
    type: Literal["heartbeat"] = "heartbeat"
    worker_id: str
    cpu_percent: float
    ram_percent: float
    gpu_percent: Optional[float] = 0.0
    running_tasks: int = 0


class TaskMsg(BaseModel):
    """Task assignment dispatched from coordinator to a worker."""
    type: Literal["task"] = "task"
    task_id: str
    job_id: str
    task_type: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)


class ResultMsg(BaseModel):
    """Task execution result returned by a worker to the coordinator."""
    type: Literal["result"] = "result"
    task_id: str
    status: Literal["ok", "error"] = "ok"
    output: Any = Field(default_factory=dict)
    duration_ms: float = 0.0


# Union of all valid protocol messages
ProtocolMsg = Union[RegisterMsg, HeartbeatMsg, TaskMsg, ResultMsg]


def parse_message(json_text: Union[str, bytes, Dict[str, Any]]) -> ProtocolMsg:
    """Parse JSON string, bytes, or dictionary into the corresponding protocol message.

    Raises:
        ValueError: If JSON is invalid, missing 'type', or specifies an unknown type.
        ValidationError: If message attributes fail schema validation.
    """
    if isinstance(json_text, (str, bytes)):
        try:
            data = json.loads(json_text)
        except Exception as e:
            raise ValueError(f"Invalid JSON message: {e}") from e
    elif isinstance(json_text, dict):
        data = json_text
    else:
        raise ValueError("Message must be a JSON string, bytes, or dictionary")

    if not isinstance(data, dict):
        raise ValueError("Message payload must be a JSON object")

    msg_type = data.get("type")
    if not msg_type:
        raise ValueError("Missing 'type' field in message")

    type_map = {
        "register": RegisterMsg,
        "heartbeat": HeartbeatMsg,
        "task": TaskMsg,
        "result": ResultMsg,
    }

    model_cls = type_map.get(msg_type)
    if model_cls is None:
        raise ValueError(f"Unknown message type: '{msg_type}'")

    return model_cls.model_validate(data)
