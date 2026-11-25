"""Unit tests for Module 2: Database Operations."""
import pytest
from coordinator.db import (
    get_job,
    get_tasks_by_job,
    get_worker,
    init_db,
    insert_job,
    insert_task,
    list_jobs,
    list_workers,
    set_worker_status,
    update_job,
    update_task,
    upsert_worker,
)


def test_init_db_creates_tables_on_fresh_file(tmp_db):
    """Verify that init_db creates workers, jobs, and tasks tables."""
    init_db(tmp_db)

    # Calling list operations should return empty lists without schema errors
    assert list_workers(tmp_db) == []
    assert list_jobs(tmp_db) == []


def test_worker_upsert_read_and_status_update(tmp_db):
    """Verify worker insertion, retrieval, and status update to dead."""
    init_db(tmp_db)

    worker_data = {
        "id": "worker-node-1",
        "hostname": "alpha.local",
        "cpu_cores": 8,
        "ram_gb": 16.0,
        "gpu_name": "NVIDIA GeForce RTX 3080",
        "vram_gb": 10.0,
        "status": "alive",
        "last_seen": 1000.0,
        "cpu_percent": 12.5,
        "ram_percent": 45.0,
        "gpu_percent": 30.0,
    }

    inserted = upsert_worker(tmp_db, worker_data)
    assert inserted["id"] == "worker-node-1"
    assert inserted["hostname"] == "alpha.local"
    assert inserted["cpu_cores"] == 8
    assert inserted["ram_gb"] == 16.0
    assert inserted["gpu_name"] == "NVIDIA GeForce RTX 3080"
    assert inserted["vram_gb"] == 10.0
    assert inserted["status"] == "alive"

    # Read back and compare
    fetched = get_worker(tmp_db, "worker-node-1")
    assert fetched is not None
    assert fetched["hostname"] == "alpha.local"
    assert fetched["cpu_cores"] == 8
    assert fetched["status"] == "alive"

    # Update status to dead
    updated = set_worker_status(tmp_db, "worker-node-1", "dead")
    assert updated is True

    # Read back again
    fetched_dead = get_worker(tmp_db, "worker-node-1")
    assert fetched_dead is not None
    assert fetched_dead["status"] == "dead"


def test_insert_job_with_three_tasks_and_count(tmp_db):
    """Verify inserting a job with 3 tasks and querying them by job ID."""
    init_db(tmp_db)

    # Insert parent job
    job = insert_job(
        tmp_db,
        id="job-100",
        type="monte_carlo_pi",
        params={"total_samples": 3000000},
        status="pending",
    )
    assert job["id"] == "job-100"
    assert job["type"] == "monte_carlo_pi"
    assert job["status"] == "pending"

    # Insert 3 tasks for the job
    t1 = insert_task(tmp_db, id="t-1", job_id="job-100", payload={"samples": 1000000, "seed": 1})
    t2 = insert_task(tmp_db, id="t-2", job_id="job-100", payload={"samples": 1000000, "seed": 2})
    t3 = insert_task(tmp_db, id="t-3", job_id="job-100", payload={"samples": 1000000, "seed": 3})

    assert t1["id"] == "t-1"
    assert t2["id"] == "t-2"
    assert t3["id"] == "t-3"

    # Query tasks by job ID
    tasks = get_tasks_by_job(tmp_db, "job-100")
    assert len(tasks) == 3
    task_ids = [t["id"] for t in tasks]
    assert task_ids == ["t-1", "t-2", "t-3"]


def test_update_job_and_task(tmp_db):
    """Verify updating job and task attributes."""
    init_db(tmp_db)

    insert_job(tmp_db, id="job-200", type="prime_count", params={"start": 1, "end": 1000})
    insert_task(tmp_db, id="task-200-1", job_id="job-200", payload={"start": 1, "end": 1000})

    job_updated = update_job(tmp_db, "job-200", status="completed", result={"count": 168})
    assert job_updated is True

    job = get_job(tmp_db, "job-200")
    assert job is not None
    assert job["status"] == "completed"

    task_updated = update_task(tmp_db, "task-200-1", status="done", result={"count": 168})
    assert task_updated is True

