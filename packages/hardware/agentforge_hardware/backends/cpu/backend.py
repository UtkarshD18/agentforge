import os
from typing import List, Dict, Any, Optional
from agentforge_hardware.interfaces import (
    HardwareBackend,
    HardwareCapabilities,
    DeviceMetrics,
    AbstractMemoryPool,
    AbstractStreamManager,
    AbstractGraphManager,
    GPUCapabilities
)

class CPUMemoryPool(AbstractMemoryPool):
    """
    Host RAM memory pool fallback.
    """
    def __init__(self) -> None:
        self._allocated = {}
        self._next_ptr = 0x100000000

    def acquire_buffer(self, size_bytes: int) -> int:
        ptr = self._next_ptr
        self._allocated[ptr] = size_bytes
        self._next_ptr += size_bytes
        return ptr

    def release_buffer(self, ptr: int) -> None:
        if ptr in self._allocated:
            del self._allocated[ptr]

class CPUStreamManager(AbstractStreamManager):
    """
    Sync CPU stream manager fallback.
    """
    def __init__(self) -> None:
        self.streams = []

    def create_stream(self, name: str) -> str:
        s = f"cpu_sync_stream_{name}"
        if s not in self.streams:
            self.streams.append(s)
        return s

    def get_streams(self) -> List[str]:
        return list(self.streams)

class CPUGraphManager(AbstractGraphManager):
    """
    Sync CPU Graph execution fallback.
    """
    def __init__(self) -> None:
        self.graphs = {}

    def record_graph(self, name: str, node_operations: List[str]) -> None:
        self.graphs[name] = list(node_operations)

    def play_graph(self, name: str) -> bool:
        return name in self.graphs

class CPUBackend(HardwareBackend):
    """
    Fallback CPU compute backend for hosts without compatible discrete GPUs.
    """
    def initialize(self) -> bool:
        return True  # CPU backend is always available

    def get_capabilities(self) -> HardwareCapabilities:
        cpu_cores = os.cpu_count() or 1
        
        # Determine total physical RAM
        total_ram = 0
        try:
            page_size = os.sysconf('SC_PAGE_SIZE')
            phys_pages = os.sysconf('SC_PHYS_PAGES')
            total_ram = page_size * phys_pages
        except Exception:
            total_ram = 8 * 1024 * 1024 * 1024  # Default 8GB fallback
            
        return HardwareCapabilities(
            cpu_cores=cpu_cores,
            total_ram_bytes=total_ram,
            gpus=[]  # No discrete GPUs in CPU backend
        )

    def get_metrics(self) -> List[DeviceMetrics]:
        # CPU backend doesn't have discrete GPU metrics, returns an empty list
        return []

    def get_memory_pool(self, device_index: int) -> AbstractMemoryPool:
        return CPUMemoryPool()

    def get_stream_manager(self, device_index: int) -> AbstractStreamManager:
        return CPUStreamManager()

    def get_graph_manager(self, device_index: int) -> AbstractGraphManager:
        return CPUGraphManager()
