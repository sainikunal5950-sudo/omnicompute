"""Database access layer for the OmniCompute coordinator using SQLite."""
import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from shared.config import DB_PATH


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize database tables with WAL mode and foreign keys enabled."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                cpu_cores INTEGER NOT NULL,
                ram_gb REAL NOT NULL,
                gpu_name TEXT,
                vram_gb REAL,
                status TEXT NOT NULL CHECK(status IN ('alive', 'dead')),
                last_seen REAL NOT NULL,
                cpu_percent REAL DEFAULT 0.0,
                ram_percent REAL DEFAULT 0.0,
                gpu_percent REAL DEFAULT 0.0
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                params TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'failed')),
                created_at REAL NOT NULL,
                finished_at REAL,
                result TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                payload TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'done', 'failed')),
                worker_id TEXT REFERENCES workers(id) ON DELETE SET NULL,
                attempts INTEGER DEFAULT 0,
                result TEXT,
                started_at REAL,
                finished_at REAL
            );
        """)
        conn.commit()


# ============================================================================
# Worker Operations
# ============================================================================


def upsert_worker(db_path: str, worker: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Insert or update a worker node record in the database."""
    data = dict(worker or {})
    data.update(kwargs)

    worker_id = data.get("id") or data.get("worker_id")
    if not worker_id:
        raise ValueError("Worker 'id' or 'worker_id' is required")

    hostname = str(data.get("hostname", "unknown"))
    cpu_cores = int(data.get("cpu_cores", 1))
    ram_gb = float(data.get("ram_gb", 1.0))
    gpu_name = data.get("gpu_name")
    vram_gb = float(data["vram_gb"]) if data.get("vram_gb") is not None else None

    # Support nested gpu dict/model if provided
    gpu = data.get("gpu")
    if isinstance(gpu, dict):
        gpu_name = gpu.get("name", gpu_name)
        vram_gb = float(gpu.get("vram_gb", vram_gb)) if gpu.get("vram_gb") is not None else None
    elif hasattr(gpu, "name") and hasattr(gpu, "vram_gb"):
        gpu_name = gpu.name
        vram_gb = float(gpu.vram_gb)

    status = str(data.get("status", "alive"))
    last_seen = float(data.get("last_seen", time.time()))
    cpu_percent = float(data.get("cpu_percent", 0.0))
    ram_percent = float(data.get("ram_percent", 0.0))
    gpu_percent = float(data.get("gpu_percent", 0.0))

    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT INTO workers (
                id, hostname, cpu_cores, ram_gb, gpu_name, vram_gb,
                status, last_seen, cpu_percent, ram_percent, gpu_percent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                hostname=excluded.hostname,
                cpu_cores=excluded.cpu_cores,
                ram_gb=excluded.ram_gb,
                gpu_name=excluded.gpu_name,
                vram_gb=excluded.vram_gb,
                status=excluded.status,
                last_seen=excluded.last_seen,
                cpu_percent=excluded.cpu_percent,
                ram_percent=excluded.ram_percent,
                gpu_percent=excluded.gpu_percent;
        """, (
            worker_id, hostname, cpu_cores, ram_gb, gpu_name, vram_gb,
            status, last_seen, cpu_percent, ram_percent, gpu_percent
        ))
        conn.commit()

    result = get_worker(db_path, worker_id)
    if result is None:
        raise RuntimeError(f"Failed to retrieve worker {worker_id} after upsert")
    return result


def get_worker(db_path: str, worker_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single worker by ID, or None if not found."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_workers(db_path: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all workers, optionally filtered by status ('alive' or 'dead')."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if status:
            cur.execute("SELECT * FROM workers WHERE status = ? ORDER BY last_seen DESC", (status,))
        else:
            cur.execute("SELECT * FROM workers ORDER BY last_seen DESC")
        return [dict(r) for r in cur.fetchall()]


def set_worker_status(db_path: str, worker_id: str, status: str) -> bool:
    """Update the status of a worker ('alive' or 'dead')."""
    if status not in ("alive", "dead"):
        raise ValueError("Status must be 'alive' or 'dead'")
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE workers SET status = ? WHERE id = ?", (status, worker_id))
        conn.commit()
        return cur.rowcount > 0


# ============================================================================
# Job Operations
# ============================================================================


def insert_job(db_path: str, job: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Insert a new compute job record."""
    data = dict(job or {})
    data.update(kwargs)

    job_id = str(data.get("id") or str(uuid.uuid4()))
    job_type = data.get("type")
    if not job_type:
        raise ValueError("Job 'type' is required")

    params = data.get("params", {})
    params_str = json.dumps(params) if isinstance(params, (dict, list)) else str(params)

    status = str(data.get("status", "pending"))
    created_at = float(data.get("created_at", time.time()))
    finished_at = float(data["finished_at"]) if data.get("finished_at") is not None else None

    result = data.get("result")
    result_str = (
        json.dumps(result)
        if isinstance(result, (dict, list))
        else (str(result) if result is not None else None)
    )

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO jobs (id, type, params, status, created_at, finished_at, result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (job_id, str(job_type), params_str, status, created_at, finished_at, result_str))
        conn.commit()

    res = get_job(db_path, job_id)
    if res is None:
        raise RuntimeError(f"Failed to retrieve job {job_id} after insert")
    return res


def get_job(db_path: str, job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single job by ID, or None if not found."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_jobs(db_path: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all jobs, optionally filtered by status."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if status:
            cur.execute("SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cur.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


def update_job(db_path: str, job_id: str, **kwargs) -> bool:
    """Update mutable fields of a job record."""
    if not kwargs:
        return False

    allowed_fields = {"type", "params", "status", "created_at", "finished_at", "result"}
    updates = []
    values = []

    for k, v in kwargs.items():
        if k in allowed_fields:
            if k in ("params", "result") and isinstance(v, (dict, list)):
                v = json.dumps(v)
            updates.append(f"{k} = ?")
            values.append(v)

    if not updates:
        return False

    values.append(job_id)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()
        return cur.rowcount > 0


# ============================================================================
# Task Operations
# ============================================================================


def insert_task(db_path: str, task: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Insert a new task associated with a parent job."""
    data = dict(task or {})
    data.update(kwargs)

    task_id = str(data.get("id") or data.get("task_id") or str(uuid.uuid4()))
    job_id = data.get("job_id")
    if not job_id:
        raise ValueError("Task 'job_id' is required")

    payload = data.get("payload", {})
    payload_str = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)

    status = str(data.get("status", "pending"))
    worker_id = data.get("worker_id")
    attempts = int(data.get("attempts", 0))

    result = data.get("result")
    result_str = (
        json.dumps(result)
        if isinstance(result, (dict, list))
        else (str(result) if result is not None else None)
    )

    started_at = float(data["started_at"]) if data.get("started_at") is not None else None
    finished_at = float(data["finished_at"]) if data.get("finished_at") is not None else None

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tasks (id, job_id, payload, status, worker_id, attempts, result, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, str(job_id), payload_str, status, worker_id, attempts, result_str, started_at, finished_at))
        conn.commit()

    res = get_task(db_path, task_id)
    if res is None:
        raise RuntimeError(f"Failed to retrieve task {task_id} after insert")
    return res


def get_task(db_path: str, task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single task by ID, or None if not found."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_tasks_by_job(db_path: str, job_id: str) -> List[Dict[str, Any]]:
    """Retrieve all tasks associated with a given job ID."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE job_id = ? ORDER BY id ASC", (job_id,))
        return [dict(r) for r in cur.fetchall()]


def update_task(db_path: str, task_id: str, **kwargs) -> bool:
    """Update mutable fields of a task record."""
    if not kwargs:
        return False

    allowed_fields = {
        "payload", "status", "worker_id", "attempts",
        "result", "started_at", "finished_at"
    }
    updates = []
    values = []

    for k, v in kwargs.items():
        if k in allowed_fields:
            if k in ("payload", "result") and isinstance(v, (dict, list)):
                v = json.dumps(v)
            updates.append(f"{k} = ?")
            values.append(v)

    if not updates:
        return False

    values.append(task_id)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()
        return cur.rowcount > 0

