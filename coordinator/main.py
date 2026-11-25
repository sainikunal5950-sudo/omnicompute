"""FastAPI server application for the OmniCompute central coordinator."""
import json
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from coordinator.db import init_db
from shared.config import DB_PATH
from shared.protocol import parse_message

logger = logging.getLogger("omnicompute.coordinator")


def create_app(db_path: Optional[str] = None) -> FastAPI:
    """Application factory for the coordinator."""
    actual_db_path = db_path if db_path is not None else DB_PATH
    init_db(actual_db_path)

    app = FastAPI(title="OmniCompute Coordinator")
    app.state.db_path = actual_db_path
    app.state.received_messages = []

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.websocket("/ws/worker")
    async def worker_websocket(websocket: WebSocket):
        """WebSocket communication endpoint for worker nodes."""
        await websocket.accept()
        try:
            while True:
                text = await websocket.receive_text()
                try:
                    msg = parse_message(text)
                    app.state.received_messages.append(msg)
                    logger.info("Worker message received: type=%s", msg.type)
                except Exception as err:
                    # Report parsing/validation error back to worker and keep connection open
                    error_payload = json.dumps({"error": str(err)})
                    await websocket.send_text(error_payload)
        except WebSocketDisconnect:
            logger.info("Worker WebSocket disconnected")
        except Exception as e:
            logger.error("WebSocket connection unexpected error: %s", e)

    return app


# Default application instance
app = create_app()

