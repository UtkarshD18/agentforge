import pytest
from agentforge_hardware.backends.intel.backend import IntelBackend
from agentforge_hardware.backends.amd.backend import AMDBackend

def test_intel_backend_capabilities():
    backend = IntelBackend()
    caps = backend.get_capabilities()
    
    assert caps.cpu_cores >= 1
    assert caps.total_ram_bytes > 0
    # GPUs can be empty if physical Intel graphics isn't present in sysfs DRM (headless testing), which is correct
    assert isinstance(caps.gpus, list)
    
    # Verify mock pool allocations
    pool = backend.get_memory_pool(device_index=0)
    ptr = pool.acquire_buffer(1024)
    assert ptr > 0
    pool.release_buffer(ptr)

def test_amd_backend_capabilities():
    backend = AMDBackend()
    caps = backend.get_capabilities()
    
    assert caps.cpu_cores >= 1
    assert caps.total_ram_bytes > 0
    assert isinstance(caps.gpus, list)
    
    # Verify stream creation
    streams = backend.get_stream_manager(device_index=0)
    s = streams.create_stream("render")
    assert "amd_stream_0_render" in s
