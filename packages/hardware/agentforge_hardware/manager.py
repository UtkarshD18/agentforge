import sys
from agentforge_hardware.registry import get_hardware_registry
from agentforge_hardware.interfaces import HardwareBackend

class HardwareManager:
    """
    Coordinates hardware auto-detection on boot.
    Scans system capabilities and registers the optimal pluggable compute backend.
    """
    @staticmethod
    def auto_detect_and_register() -> HardwareBackend:
        registry = get_hardware_registry()

        # 1. Attempt to load and initialize NVIDIA CUDA/NVML Backend
        try:
            from agentforge_hardware.backends.nvidia.backend import NvidiaBackend
            nvidia_backend = NvidiaBackend()
            if nvidia_backend.initialize():
                registry.register_backend(nvidia_backend)
                return nvidia_backend
        except (ImportError, Exception):
            pass

        # 2. Attempt to load and initialize AMD ROCm/HIP Backend
        try:
            from agentforge_hardware.backends.amd.backend import AMDBackend
            amd_backend = AMDBackend()
            if amd_backend.initialize():
                registry.register_backend(amd_backend)
                return amd_backend
        except (ImportError, Exception):
            pass

        # 3. Fallback: Load and initialize CPU Backend
        from agentforge_hardware.backends.cpu.backend import CPUBackend
        cpu_backend = CPUBackend()
        cpu_backend.initialize()
        registry.register_backend(cpu_backend)
        return cpu_backend
