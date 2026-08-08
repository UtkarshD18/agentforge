import time
import pytest
from agentforge_hardware.broker import get_device_broker
from agentforge_hardware.queue import ComputeQueue
from agentforge_hardware.manager import HardwareManager

def test_broker_vram_bounds():
    # Detect active backend (resolves CPU or Nvidia)
    HardwareManager.auto_detect_and_register()
    
    broker = get_device_broker()
    # Reset reservation
    broker.release_vram(device_index=0, bytes_released=9999999999999)
    
    # Attempt to reserve a huge invalid chunk (e.g. 10 Terabytes)
    huge_bytes = 10 * 1024**4
    assert broker.reserve_vram(device_index=0, bytes_requested=huge_bytes) is False
    
    # Attempt to reserve a small safe chunk (e.g. 10 Megabytes)
    safe_bytes = 10 * 1024**2
    assert broker.reserve_vram(device_index=0, bytes_requested=safe_bytes) is True
    
    # Release memory
    broker.release_vram(device_index=0, bytes_released=safe_bytes)
    assert broker.get_reservations(device_index=0)["vram_reserved_bytes"] == 0

def test_compute_queue_processing():
    HardwareManager.auto_detect_and_register()
    
    # Setup queue for device 0
    device_queue = ComputeQueue(device_index=0, device_name="TestDevice-0")
    device_queue.start()
    
    task_runs = []
    def mock_task_action():
        task_runs.append("run-success")
        
    # Submit task requesting 10MB VRAM
    device_queue.submit_task(
        task_name="render_overlay",
        vram_required_bytes=10 * 1024**2,
        action=mock_task_action
    )
    
    # Wait briefly for thread execution
    timeout = 1.0
    start = time.time()
    while len(task_runs) == 0 and time.time() - start < timeout:
        time.sleep(0.05)
        
    device_queue.stop()
    
    assert len(task_runs) == 1
    assert task_runs[0] == "run-success"
