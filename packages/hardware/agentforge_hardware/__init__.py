# AgentForge Hardware Abstraction Layer (HAL)
from .discovery import discover_hardware_capabilities, is_nvml_available, GPUCapabilities, HardwareCapabilities
from .monitor import get_gpu_metrics, GPUMetrics
from .supervisor import HardwareSupervisor
from .gpu.memory import GPUFrame, CUDAMemoryPool
from .gpu.streams import CUDAStreamManager
from .gpu.graphs import CUDAGraphManager
