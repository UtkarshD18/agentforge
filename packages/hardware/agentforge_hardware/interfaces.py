from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AcceleratorFrame(BaseModel):
    """
    Metadata representation of a pixel frame allocated on hardware accelerator memory.
    Ensures zero-copy frame transmissions between processing and render nodes.
    """
    memory_pointer: int
    width: int
    height: int
    format: str = "nv12"                  # Codec format (e.g. nv12, rgba)
    timestamp_seconds: float
    device_index: int = 0
    backend_type: str = "cpu"             # 'cuda', 'hip', 'metal', 'cpu'
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GPUCapabilities(BaseModel):
    """
    Vendor-agnostic hardware features for a single GPU card.
    """
    index: int
    name: str
    total_vram_bytes: int
    cuda_version: Optional[str] = None    # Set if NVIDIA
    rocm_version: Optional[str] = None    # Set if AMD
    driver_version: Optional[str] = None
    has_hardware_decode: bool = False     # NVDEC, AMF decoder, etc.
    has_hardware_encode: bool = False     # NVENC, AMF encoder, etc.
    has_tensor_cores: bool = False

class HardwareCapabilities(BaseModel):
    """
    Full system hardware profile.
    """
    cpu_cores: int
    total_ram_bytes: int
    gpus: List[GPUCapabilities] = []

class DeviceMetrics(BaseModel):
    """
    Real-time telemetry metrics for a computing device.
    """
    device_index: int
    compute_utilization_percent: float
    memory_utilization_percent: float
    memory_used_bytes: int
    memory_free_bytes: int
    temperature_celsius: float = 0.0
    power_draw_watts: float = 0.0

class AbstractMemoryPool(ABC):
    """
    Abstract interface for pre-allocated hardware accelerator memory pooling.
    """
    @abstractmethod
    def acquire_buffer(self, size_bytes: int) -> int:
        pass

    @abstractmethod
    def release_buffer(self, ptr: int) -> None:
        pass

class AbstractStreamManager(ABC):
    """
    Abstract interface for parallel execution streams.
    """
    @abstractmethod
    def create_stream(self, name: str) -> str:
        pass

    @abstractmethod
    def get_streams(self) -> List[str]:
        pass

class AbstractGraphManager(ABC):
    """
    Abstract interface for graph record/replay pipelines.
    """
    @abstractmethod
    def record_graph(self, name: str, node_operations: List[str]) -> None:
        pass

    @abstractmethod
    def play_graph(self, name: str) -> bool:
        pass

class HardwareBackend(ABC):
    """
    Base class representing a vendor-specific hardware compute backend.
    """
    @abstractmethod
    def initialize(self) -> bool:
        """
        Attempts to initialize backend drivers. Returns True if successful.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> HardwareCapabilities:
        """
        Returns static system specs for CPUs, RAM, and GPUs.
        """
        pass

    @abstractmethod
    def get_metrics(self) -> List[DeviceMetrics]:
        """
        Returns real-time telemetry metrics for all devices.
        """
        pass

    @abstractmethod
    def get_memory_pool(self, device_index: int) -> AbstractMemoryPool:
        pass

    @abstractmethod
    def get_stream_manager(self, device_index: int) -> AbstractStreamManager:
        pass

    @abstractmethod
    def get_graph_manager(self, device_index: int) -> AbstractGraphManager:
        pass
