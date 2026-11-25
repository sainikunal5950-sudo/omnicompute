# OmniCompute Implementation Progress

This document tracks the incremental implementation of OmniCompute across 10 structured modules.
Each module is built, tested, and verified independently before proceeding to the next.

---

## Module Checklist

- [x] **Module 1: Foundation and Protocol**
  - Define `shared/protocol.py` (Pydantic models for `register`, `heartbeat`, `task`, `result`, job submission, and cluster state).
  - Define `shared/config.py` (default ports, timeouts, thresholds, and limits).
  - Unit tests: `tests/test_m1_protocol.py`.

- [x] **Module 2: Coordinator Core and Database**
  - Implement `coordinator/db.py` (SQLite schema initialization, connection management, worker/job/task CRUD).
  - Implement `coordinator/main.py` (FastAPI app, WebSocket endpoint for workers, REST API for jobs and cluster status).
  - Unit tests: `tests/test_m2_coordinator.py`.

- [ ] **Module 3: Worker Agent and Hardware Detection**
  - Implement `worker/hardware.py` (CPU, RAM, and GPU detection with fallback to CPU).
  - Implement `worker/agent.py` (WebSocket client, registration, connection loop).
  - Unit tests: `tests/test_m3_worker.py`.

- [ ] **Module 4: Heartbeat, Failure Detection, and Reassignment**
  - Implement `coordinator/registry.py` (active connection manager, thread-safe worker tracking).
  - Implement `coordinator/monitor.py` (background heartbeat watchdog, dead worker detection, task reset & reassignment).
  - Unit tests: `tests/test_m4_monitor.py`.

- [ ] **Module 5: Job Management and Task Splitting**
  - Implement `coordinator/jobs.py` (job validation, splitting strategies for `monte_carlo_pi`, `prime_count`, `matrix_multiply`, `ml_train`).
  - Unit tests: `tests/test_m5_jobs.py`.

- [ ] **Module 6: Resource-Aware Scheduler and Load Balancer**
  - Implement `coordinator/scheduler.py` (task queue polling, GPU preference matching, CPU fallback, load score balancing).
  - Unit tests: `tests/test_m6_scheduler.py`.

- [ ] **Module 7: Task Executors**
  - Implement `worker/executor.py` (dispatcher for built-in tasks).
  - Implement `worker/tasks/` (`monte_carlo_pi.py`, `prime_count.py`, `matrix_multiply.py`, `ml_train.py`).
  - Unit tests: `tests/test_m7_executor.py`.

- [ ] **Module 8: Result Aggregation**
  - Implement `coordinator/aggregator.py` (collect task results, verify completion, execute merge logic, update job status).
  - Unit tests: `tests/test_m8_aggregator.py`.

- [ ] **Module 9: Monitoring Dashboard**
  - Implement `dashboard/index.html` (pure HTML UI for job submission, worker table, and job status).
  - Implement `dashboard/app.js` (vanilla JS for live WebSocket updates and REST API calls).
  - Unit tests: `tests/test_m9_dashboard.py`.

- [ ] **Module 10: Distributed ML Experiment, Benchmark, and Report**
  - Implement benchmark scripts for multi-worker CPU vs. GPU performance comparison.
  - End-to-end integration test and experiment validation.
  - Unit tests: `tests/test_m10_benchmark.py`.

---

## Notes

1. **Coding Rules**:
   - Short, readable functions with clear type hints.
   - Code written in simple, clean Python without extra unneeded dependencies or heavy frameworks.
   - Comments written in simple English explaining non-obvious logic.
   - Finished modules are frozen and never modified unless explicitly requested.

2. **Testing Rules**:
   - Each module `N` has corresponding tests in `tests/test_m<N>_<name>.py`.
   - Tests execute via: `python run_tests.py <N>`.
   - Tests must be completely self-contained: no external internet access, no hardcoded ports (use `free_port` fixture), and no requirement for physical GPUs (use mocks or monkeypatching).
   - Temporary test databases must use the `tmp_db` fixture.
   - Passing tests must never be deleted or weakened to make subsequent tests pass.

