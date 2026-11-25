"""In-memory active worker connection registry and database sync."""
import logging
import time
from typing import Any, Dict, Optional
from fastapi import WebSocket

from coordinator.db import upsert_worker
from shared.protocol import RegisterMsg

logger = logging.getLogger("omnicompute.coordinator.registry")


class WorkerRegistry:
    """Tracks active worker WebSocket connections and synchronizes state to SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.active_workers: Dict[str, WebSocket] = {}

    def register(self, msg: RegisterMsg, websocket: WebSocket) -> Dict[str, Any]:
        """Save/update worker in DB with status alive and track active WebSocket connection."""
        gpu_name = msg.gpu.name if msg.gpu else None
        vram_gb = msg.gpu.vram_gb if msg.gpu else None

        worker_record = upsert_worker(
            self.db_path,
            id=msg.worker_id,
            hostname=msg.hostname,
            cpu_cores=msg.cpu_cores,
            ram_gb=msg.ram_gb,
            gpu_name=gpu_name,
            vram_gb=vram_gb,
            status="alive",
            last_seen=time.time(),
        )

        self.active_workers[msg.worker_id] = websocket
        logger.info("Worker registered: id=%s (total active: %d)", msg.worker_id, len(self.active_workers))
        return worker_record

    def unregister(self, worker_id: str) -> None:
        """Remove worker from active in-memory connections."""
        if worker_id in self.active_workers:
            del self.active_workers[worker_id]
            logger.info("Worker unregistered: id=%s (total active: %d)", worker_id, len(self.active_workers))

    def get_socket(self, worker_id: str) -> Optional[WebSocket]:
        """Get the active WebSocket connection for a given worker ID."""
        return self.active_workers.get(worker_id)

    def is_connected(self, worker_id: str) -> bool:
        """Check if worker is currently connected via WebSocket."""
        return worker_id in self.active_workers

