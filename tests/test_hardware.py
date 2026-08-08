import time
import pytest
from agentforge_core.di import get_container
from agentforge_core.events import Event, get_event_bus
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository
from agentforge_hardware import (
    discover_hardware_capabilities,
    is_nvml_available,
    HardwareSupervisor,
    GPUFrame,
    CUDAMemoryPool,
    CUDAStreamManager,
    CUDAGraphManager
)

def test_system_discovery():
    caps = discover_hardware_capabilities()
    assert caps.cpu_cores >= 1
    assert caps.total_ram_bytes > 0
    # On CPU-only environments (CI/CD) gpus list can be empty, which is a correct fallback
    assert isinstance(caps.gpus, list)

def test_gpu_memory_pool():
    pool = CUDAMemoryPool(device_index=0, pool_size_mb=128)
    ptr = pool.acquire_buffer(1024)
    assert ptr > 0
    assert ptr in pool._allocated_pointers
    assert pool._allocated_pointers[ptr] == 1024
    
    pool.release_buffer(ptr)
    assert ptr not in pool._allocated_pointers

def test_gpu_frame_validation():
    frame = GPUFrame(
        cuda_pointer=13963456789012,
        width=1920,
        height=1080,
        format="nv12",
        timestamp_seconds=42.0
    )
    assert frame.cuda_pointer == 13963456789012
    assert frame.width == 1920
    assert frame.format == "nv12"

def test_cuda_stream_and_graph():
    stream_mgr = CUDAStreamManager(device_index=0)
    stream = stream_mgr.create_stream("render")
    assert "cuda_stream_0_render" in stream
    assert "render" in stream_mgr.get_streams()
    
    graph_mgr = CUDAGraphManager()
    graph_mgr.record_graph("blur_and_crop", ["crop", "resize", "blur"])
    assert graph_mgr.play_graph("blur_and_crop") is True
    assert graph_mgr.play_graph("non_existent") is False

def test_hardware_supervisor_registration():
    # Setup database environment
    container = get_container()
    container.clear()
    
    repo = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, repo)
    
    # Track Event Bus alerts
    events = []
    def track_events(e: Event):
        events.append(e)
    get_event_bus().subscribe(track_events)
    
    # Run Hardware Supervisor
    supervisor = HardwareSupervisor(check_interval_seconds=0.1)
    supervisor.start()
    
    # Check that supervisor registered hardware nodes in the DB
    cpu = repo.get_entity("hardware://cpu-0")
    assert cpu is not None
    assert cpu.type == "hardware"
    assert cpu.metadata["cores"] > 0
    
    ram = repo.get_entity("hardware://ram-0")
    assert ram is not None
    assert ram.metadata["total_gb"] > 0
    
    # Stop supervisor and unsubscribe
    supervisor.stop()
    get_event_bus().unsubscribe(track_events)
