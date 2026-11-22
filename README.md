# OmniCompute: A Distributed GPU and CPU Computing Network

OmniCompute is a lightweight, distributed computing platform in Python that aggregates idle CPU and GPU compute power across networked machines. A central coordinator distributes compute workloads across connected worker agents, monitors node health, automatically handles worker failures with task reassignment, and reports real-time cluster metrics to a web dashboard.

---

## Key Features

- **Resource-Aware Scheduling**: Dynamically schedules tasks to CPU or GPU workers based on workload requirements and live resource availability.
- **Heterogeneous Cluster Support**: Nodes can participate with CPU-only or with CPU + GPU (NVIDIA CUDA via `nvidia-smi` / `torch.cuda`).
- **Resilient Fault Tolerance**: Heartbeat tracking detects offline or crashed workers and reassigns incomplete tasks seamlessly.
- **Built-in Safe Compute Tasks**: Workers run pre-defined, parameterized tasks (Monte Carlo Pi, Prime Counting, Distributed Matrix Multiplication, and Distributed ML Training); arbitrary remote code execution is strictly prohibited.
- **Live Real-Time Dashboard**: Pure HTML and vanilla JavaScript dashboard served over WebSockets and HTTP for real-time monitoring and job submission.

---

## Project Structure

```text
omnicompute/
  shared/          # Protocol definitions (Pydantic schemas) and configuration
  coordinator/     # Central coordinator: REST/WebSocket API, DB, scheduler, monitor, aggregator
  worker/          # Worker agent: WebSocket client, hardware probing, task executors
  dashboard/       # Web UI: plain HTML5 and JavaScript (no frameworks)
  tests/           # Automated pytest test suites per module
  docs/            # Architecture and progress documentation
requirements.txt   # Core Python dependencies
README.md          # Project overview and quick start guide
```

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Optional: NVIDIA GPU with CUDA drivers (CPU fallback is always supported)

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## How to Run *(To be completed as modules are implemented)*

### 1. Start the Central Coordinator
```bash
# To be completed (Module 2)
# python -m omnicompute.coordinator.main
```

### 2. Start Worker Agents
```bash
# To be completed (Module 3)
# python -m omnicompute.worker.agent --coordinator ws://localhost:8000/ws/worker
```

### 3. Open the Dashboard
```bash
# To be completed (Module 9)
# Visit http://localhost:8000 in your browser
```

---

## Running Tests

Automated testing is configured per module (`N` = module number from 1 to 10):

```bash
python run_tests.py <N>
```
All tests run locally without requiring active network connections, fixed ports, or physical GPUs.

