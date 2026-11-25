"""Hardware detection utilities for worker nodes using psutil, nvidia-smi, and torch."""
import logging
import shutil
import subprocess
from typing import Any, Dict, Optional
import psutil

logger = logging.getLogger("omnicompute.worker.hardware")


def detect_nvidia_smi() -> Optional[Dict[str, Any]]:
    """Query GPU specifications using the nvidia-smi command-line tool.

    Returns:
        Dict with 'name' and 'vram_gb' if successful, None otherwise.
    """
    if not shutil.which("nvidia-smi"):
        return None

    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.total",
            "--format=csv,noheader,nounits",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        line = result.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            name = parts[0]
            mem_mb = float(parts[1])
            vram_gb = round(mem_mb / 1024.0, 2)
            return {"name": name, "vram_gb": vram_gb}
    except Exception as exc:
        logger.debug("nvidia-smi detection failed: %s", exc)
        return None

    return None


def detect_torch_cuda() -> Optional[Dict[str, Any]]:
    """Query GPU specifications using PyTorch CUDA if available.

    Returns:
        Dict with 'name' and 'vram_gb' if successful, None otherwise.
    """
    try:
        import torch
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            vram_gb = round(props.total_memory / (1024.0 ** 3), 2)
            return {"name": name, "vram_gb": vram_gb}
    except Exception as exc:
        logger.debug("torch.cuda detection failed: %s", exc)
        return None

    return None


def detect() -> Dict[str, Any]:
    """Detect local CPU cores, RAM, and optional GPU specifications.

    Guaranteed never to raise an unhandled exception.

    Returns:
        Dict with keys:
            cpu_cores: int (>= 1)
            ram_gb: float (> 0)
            gpu: Optional[Dict[str, Any]] ({'name': str, 'vram_gb': float} or None)
    """
    # 1. CPU detection
    try:
        cpu_cores = psutil.cpu_count(logical=True) or 1
    except Exception:
        cpu_cores = 1

    # 2. RAM detection
    try:
        ram_bytes = psutil.virtual_memory().total
        ram_gb = round(ram_bytes / (1024.0 ** 3), 2)
    except Exception:
        ram_gb = 1.0

    # 3. GPU detection (nvidia-smi first, then torch.cuda fallback)
    gpu = None
    try:
        gpu = detect_nvidia_smi()
    except Exception as exc:
        logger.debug("Error during detect_nvidia_smi: %s", exc)
        gpu = None

    if gpu is None:
        try:
            gpu = detect_torch_cuda()
        except Exception as exc:
            logger.debug("Error during detect_torch_cuda: %s", exc)
            gpu = None

    return {
        "cpu_cores": max(1, cpu_cores),
        "ram_gb": max(0.1, ram_gb),
        "gpu": gpu,
    }

