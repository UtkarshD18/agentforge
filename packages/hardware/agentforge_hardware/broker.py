import threading
from typing import Dict, Any
from agentforge_hardware.registry import get_hardware_registry

class DeviceBroker:
    """
    Device Broker tracking resource reservations (VRAM, encoder/decoder channels)
    to prevent hardware collisions and Out-Of-Memory (OOM) exceptions.
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vram_reserved: Dict[int, int] = {}       # device_index -> reserved_bytes
        self._encoders_reserved: Dict[int, int] = {}   # device_index -> active_sessions
        self._decoders_reserved: Dict[int, int] = {}   # device_index -> active_sessions

    def reserve_vram(self, device_index: int, bytes_requested: int) -> bool:
        """
        Attempts to reserve a VRAM chunk. Returns True if successful.
        """
        try:
            backend = get_hardware_registry().get_backend()
            caps = backend.get_capabilities()
        except Exception:
            # Fallback if no backend registered (e.g. testing)
            return True

        with self._lock:
            # CPU fallback check: if index matches CPU or no GPUs exist
            if not caps.gpus or device_index >= len(caps.gpus):
                # Host RAM fallback - check against host total RAM
                current = self._vram_reserved.get(device_index, 0)
                if current + bytes_requested <= caps.total_ram_bytes:
                    self._vram_reserved[device_index] = current + bytes_requested
                    return True
                return False

            gpu = caps.gpus[device_index]
            current = self._vram_reserved.get(device_index, 0)
            
            # Leave a strict 512MB headroom buffer for OS rendering
            headroom = 512 * 1024 * 1024
            if current + bytes_requested + headroom <= gpu.total_vram_bytes:
                self._vram_reserved[device_index] = current + bytes_requested
                return True
            return False

    def release_vram(self, device_index: int, bytes_released: int) -> None:
        """
        Releases reserved VRAM capacity.
        """
        with self._lock:
            current = self._vram_reserved.get(device_index, 0)
            self._vram_reserved[device_index] = max(0, current - bytes_released)

    def reserve_encoder(self, device_index: int, max_sessions: int = 4) -> bool:
        """
        Reserves an encoder channel. NVIDIA limits consumer cards to 5 concurrent sessions.
        """
        with self._lock:
            current = self._encoders_reserved.get(device_index, 0)
            if current < max_sessions:
                self._encoders_reserved[device_index] = current + 1
                return True
            return False

    def release_encoder(self, device_index: int) -> None:
        with self._lock:
            current = self._encoders_reserved.get(device_index, 0)
            self._encoders_reserved[device_index] = max(0, current - 1)

    def reserve_decoder(self, device_index: int, max_sessions: int = 8) -> bool:
        """
        Reserves a decoder channel.
        """
        with self._lock:
            current = self._decoders_reserved.get(device_index, 0)
            if current < max_sessions:
                self._decoders_reserved[device_index] = current + 1
                return True
            return False

    def release_decoder(self, device_index: int) -> None:
        with self._lock:
            current = self._decoders_reserved.get(device_index, 0)
            self._decoders_reserved[device_index] = max(0, current - 1)

    def get_reservations(self, device_index: int) -> Dict[str, Any]:
        """
        Returns active reservations for diagnostic visualization.
        """
        with self._lock:
            return {
                "vram_reserved_bytes": self._vram_reserved.get(device_index, 0),
                "encoders_active": self._encoders_reserved.get(device_index, 0),
                "decoders_active": self._decoders_reserved.get(device_index, 0)
            }

# Global singleton broker
_global_broker = DeviceBroker()

def get_device_broker() -> DeviceBroker:
    """
    Access the global singleton Device Broker.
    """
    return _global_broker
