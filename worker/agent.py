"""Worker agent client for OmniCompute cluster."""
import argparse
import asyncio
import logging
import os
import socket
import sys
import uuid
from typing import Optional
import websockets

from shared.config import HOST, PORT
from shared.protocol import GpuInfo, RegisterMsg
from worker.hardware import detect

logger = logging.getLogger("omnicompute.worker.agent")


def next_delay(attempt: int) -> int:
    """Compute exponential backoff delay in seconds: 1, 2, 4, 8 ... up to 30.

    Args:
        attempt: Non-negative reconnect retry attempt count.

    Returns:
        Delay in seconds capped at 30.
    """
    if attempt <= 0:
        return 1
    delay = 2 ** attempt
    return min(30, delay)


def get_or_create_worker_id(id_file: str = ".worker_id") -> str:
    """Generate or load a persistent worker ID (hostname + random suffix)."""
    hostname = socket.gethostname()
    if os.path.exists(id_file):
        try:
            with open(id_file, "r", encoding="utf-8") as f:
                saved_id = f.read().strip()
                if saved_id:
                    return saved_id
        except Exception as e:
            logger.warning("Could not read worker id file %s: %s", id_file, e)

    unique_suffix = uuid.uuid4().hex[:8]
    worker_id = f"{hostname}-{unique_suffix}"
    try:
        with open(id_file, "w", encoding="utf-8") as f:
            f.write(worker_id)
    except Exception as e:
        logger.warning("Could not write worker id file %s: %s", id_file, e)

    return worker_id


class WorkerAgent:
    """Worker client connecting to coordinator WebSocket and handling tasks."""

    def __init__(self, server_url: str, id_file: str = ".worker_id"):
        self.server_url = server_url
        self.worker_id = get_or_create_worker_id(id_file)
        self.hostname = socket.gethostname()
        self.running = True

    def build_register_message(self) -> RegisterMsg:
        """Inspect hardware and construct RegisterMsg."""
        hw = detect()
        gpu = GpuInfo(**hw["gpu"]) if hw.get("gpu") else None
        return RegisterMsg(
            worker_id=self.worker_id,
            hostname=self.hostname,
            cpu_cores=hw["cpu_cores"],
            ram_gb=hw["ram_gb"],
            gpu=gpu,
        )

    async def run(self, max_reconnects: Optional[int] = None) -> None:
        """Connect to coordinator and automatically reconnect if disconnected."""
        attempts = 0
        while self.running:
            if max_reconnects is not None and attempts >= max_reconnects:
                logger.info("Reached maximum reconnect attempts (%d). Exiting.", max_reconnects)
                break

            try:
                logger.info("Connecting to coordinator at %s...", self.server_url)
                async with websockets.connect(self.server_url) as ws:
                    logger.info("Connected to coordinator. Registering worker %s...", self.worker_id)
                    reg_msg = self.build_register_message()
                    await ws.send(reg_msg.model_dump_json())
                    attempts = 0  # Reset reconnect counter on successful connection

                    async for message in ws:
                        logger.info("Received message: %s", message)
            except (websockets.exceptions.WebSocketException, OSError) as exc:
                delay = next_delay(attempts)
                attempts += 1
                logger.warning(
                    "Connection failed (%s). Reconnecting in %d seconds (attempt %d)...",
                    exc, delay, attempts
                )
                await asyncio.sleep(delay)
            except Exception as exc:
                logger.error("Unexpected error in worker loop: %s", exc)
                delay = next_delay(attempts)
                attempts += 1
                await asyncio.sleep(delay)


def main() -> None:
    """CLI entrypoint for worker agent."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="OmniCompute Worker Agent")
    parser.add_argument(
        "--server",
        default=f"ws://{HOST}:{PORT}/ws/worker",
        help="Coordinator WebSocket URL",
    )
    parser.add_argument(
        "--id-file",
        default=".worker_id",
        help="Path to local worker ID cache file",
    )
    args = parser.parse_args()

    agent = WorkerAgent(server_url=args.server, id_file=args.id_file)
    logger.info("Starting Worker Agent with ID: %s", agent.worker_id)
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")


if __name__ == "__main__":
    main()

