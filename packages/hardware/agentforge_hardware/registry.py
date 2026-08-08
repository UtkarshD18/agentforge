import threading
from typing import Optional
from agentforge_hardware.interfaces import HardwareBackend

class HardwareRegistry:
    """
    Thread-safe registry for managing the active hardware backend instance.
    """
    def __init__(self) -> None:
        self._active_backend: Optional[HardwareBackend] = None
        self._lock = threading.Lock()

    def register_backend(self, backend: HardwareBackend) -> None:
        """
        Registers the compute backend to use for system queries and VRAM allocations.
        """
        with self._lock:
            self._active_backend = backend

    def get_backend(self) -> HardwareBackend:
        """
        Returns the active hardware backend.
        Raises RuntimeError if no backend has been initialized and registered.
        """
        with self._lock:
            if not self._active_backend:
                raise RuntimeError("No Hardware compute backend has been registered in the HAL.")
            return self._active_backend

# Global singleton Registry
_global_registry = HardwareRegistry()

def get_hardware_registry() -> HardwareRegistry:
    """
    Access the global singleton Hardware Registry.
    """
    return _global_registry
