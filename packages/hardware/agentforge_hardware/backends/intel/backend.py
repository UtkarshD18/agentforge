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

class IntelMemoryPool(AbstractMemoryPool):
    """
    Host Shared RAM Memory Pool implementation for Intel Integrated GPU devices.
    """
    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self._allocated: Dict[int, int] = {}
        self._next_ptr = 0x8f0000000000 + (device_index * 0x100000000)

    def acquire_buffer(self, size_bytes: int) -> int:
        ptr = self._next_ptr
        self._allocated[ptr] = size_bytes
        self._next_ptr += size_bytes
        return ptr

    def release_buffer(self, ptr: int) -> None:
        if ptr in self._allocated:
            del self._allocated[ptr]

class IntelStreamManager(AbstractStreamManager):
    """
    Intel execution streams manager.
    """
    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self._streams: List[str] = []

    def create_stream(self, name: str) -> str:
        stream_id = f"intel_stream_{self.device_index}_{name}"
        if stream_id not in self._streams:
            self._streams.append(stream_id)
        return stream_id

    def get_streams(self) -> List[str]:
        return list(self._streams)

class IntelGraphManager(AbstractGraphManager):
    """
    Intel Graph execution filter manager.
    """
    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self._recorded: Dict[str, List[str]] = {}

    def record_graph(self, name: str, node_operations: List[str]) -> None:
        self._recorded[name] = list(node_operations)

    def play_graph(self, name: str) -> bool:
        return name in self._recorded

class IntelBackend(HardwareBackend):
    """
    Intel HD/Iris/Arc graphics compute backend discovering cards via Linux DRM.
    """
    def initialize(self) -> bool:
        # Check for presence of Intel hardware vendor tag (0x8086) in DRM devices
        drm_path = "/sys/class/drm"
        if not os.path.exists(drm_path):
            return False
            
        try:
            for card in os.listdir(drm_path):
                if card.startswith("card"):
                    vendor_file = os.path.join(drm_path, card, "device", "vendor")
                    if os.path.exists(vendor_file):
                        with open(vendor_file, "r") as f:
                            vendor_id = f.read().strip()
                            if "0x8086" in vendor_id:
                                return True
        except Exception:
            pass
        return False

    def get_capabilities(self) -> HardwareCapabilities:
        cpu_cores = os.cpu_count() or 1
        
        # Query Physical Host RAM
        total_ram = 0
        try:
            page_size = os.sysconf('SC_PAGE_SIZE')
            phys_pages = os.sysconf('SC_PHYS_PAGES')
            total_ram = page_size * phys_pages
        except Exception:
            total_ram = 8 * 1024 * 1024 * 1024
            
        gpus: List[GPUCapabilities] = []
        
        # Read DRM devices
        drm_path = "/sys/class/drm"
        if os.path.exists(drm_path):
            idx = 0
            for card in os.listdir(drm_path):
                if card.startswith("card"):
                    vendor_file = os.path.join(drm_path, card, "device", "vendor")
                    if os.path.exists(vendor_file):
                        with open(vendor_file, "r") as f:
                            vendor_id = f.read().strip()
                            if "0x8086" in vendor_id:
                                # integrated graphics uses shared memory. Designate 25% of RAM.
                                shared_vram = int(total_ram * 0.25)
                                gpus.append(GPUCapabilities(
                                    index=idx,
                                    name="Intel Iris/HD Graphics (Integrated)",
                                    total_vram_bytes=shared_vram,
                                    has_hardware_decode=True,
                                    has_hardware_encode=True
                                ))
                                idx += 1
                                
        return HardwareCapabilities(
            cpu_cores=cpu_cores,
            total_ram_bytes=total_ram,
            gpus=gpus
        )

    def get_metrics(self) -> List[DeviceMetrics]:
        metrics_list: List[DeviceMetrics] = []
        caps = self.get_capabilities()
        for gpu in caps.gpus:
            metrics_list.append(DeviceMetrics(
                device_index=gpu.index,
                compute_utilization_percent=15.0,
                memory_utilization_percent=20.0,
                memory_used_bytes=int(gpu.total_vram_bytes * 0.20),
                memory_free_bytes=int(gpu.total_vram_bytes * 0.80)
            ))
        return metrics_list

    def get_memory_pool(self, device_index: int) -> AbstractMemoryPool:
        return IntelMemoryPool(device_index)

    def get_stream_manager(self, device_index: int) -> AbstractStreamManager:
        return IntelStreamManager(device_index)

    def get_graph_manager(self, device_index: int) -> AbstractGraphManager:
        return IntelGraphManager(device_index)
