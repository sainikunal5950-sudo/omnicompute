"""Unit tests for Module 3: Hardware detection and backoff logic."""
import pytest
from worker.agent import next_delay
from worker.hardware import detect, detect_nvidia_smi


def test_detect_returns_valid_hardware_spec():
    """Verify detect returns cpu_cores >= 1, ram_gb > 0, and valid gpu structure."""
    hw = detect()
    assert isinstance(hw, dict)
    assert "cpu_cores" in hw
    assert "ram_gb" in hw
    assert "gpu" in hw

    assert hw["cpu_cores"] >= 1
    assert hw["ram_gb"] > 0.0

    gpu = hw["gpu"]
    if gpu is not None:
        assert isinstance(gpu, dict)
        assert "name" in gpu
        assert isinstance(gpu["name"], str)
        assert "vram_gb" in gpu
        assert gpu["vram_gb"] >= 0.0


def test_detect_with_failing_nvidia_smi_does_not_crash(monkeypatch):
    """Verify detect gracefully falls back to gpu=None when nvidia-smi fails."""
    def fake_nvidia_smi_fail():
        raise RuntimeError("nvidia-smi error simulation")

    monkeypatch.setattr("worker.hardware.detect_nvidia_smi", fake_nvidia_smi_fail)

    # If torch is also mocked or absent, gpu must be None
    def fake_torch_cuda_fail():
        return None

    monkeypatch.setattr("worker.hardware.detect_torch_cuda", fake_torch_cuda_fail)

    hw = detect()
    assert hw["cpu_cores"] >= 1
    assert hw["ram_gb"] > 0.0
    assert hw["gpu"] is None


def test_next_delay_doubles_up_to_thirty():
    """Verify next_delay gives 1, 2, 4, 8, 16, 30 up to max 30."""
    assert next_delay(0) == 1
    assert next_delay(1) == 2
    assert next_delay(2) == 4
    assert next_delay(3) == 8
    assert next_delay(4) == 16
    assert next_delay(5) == 30
    assert next_delay(6) == 30
    assert next_delay(10) == 30

