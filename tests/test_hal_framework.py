import pytest
from agentforge_hardware.interfaces import HardwareBackend, AcceleratorFrame
from agentforge_hardware.registry import get_hardware_registry
from agentforge_hardware.manager import HardwareManager
from agentforge_hardware.backends.nvidia.backend import NvidiaBackend
from agentforge_hardware.backends.cpu.backend import CPUBackend

def test_hal_manager_fallback():
    # Execute auto-discovery
    backend = HardwareManager.auto_detect_and_register()
    
    # Verify the registry reflects this
    assert backend is not None
    registry = get_hardware_registry()
    assert registry.get_backend() is backend
    
    assert isinstance(backend, (NvidiaBackend, CPUBackend))

def test_cpu_backend_capabilities():
    backend = CPUBackend()
    caps = backend.get_capabilities()
    
    assert caps.cpu_cores >= 1
    assert caps.total_ram_bytes > 0
    assert len(caps.gpus) == 0

def test_cpu_memory_pool():
    backend = CPUBackend()
    pool = backend.get_memory_pool(device_index=0)
    
    ptr = pool.acquire_buffer(2048)
    assert ptr > 0
    
    pool.release_buffer(ptr)

def test_cpu_stream_and_graph():
    backend = CPUBackend()
    streams = backend.get_stream_manager(device_index=0)
    
    stream_name = streams.create_stream("audio")
    assert "cpu_sync_stream_audio" in stream_name
    assert stream_name in streams.get_streams()
    
    graphs = backend.get_graph_manager(device_index=0)
    graphs.record_graph("normalize", ["volume", "lufs"])
    assert graphs.play_graph("normalize") is True
    assert graphs.play_graph("unknown") is False

def test_accelerator_frame_metadata():
    frame = AcceleratorFrame(
        memory_pointer=0x10000200,
        width=1280,
        height=720,
        format="rgba",
        timestamp_seconds=12.5,
        backend_type="cpu"
    )
    assert frame.memory_pointer == 0x10000200
    assert frame.backend_type == "cpu"
    assert frame.width == 1280
