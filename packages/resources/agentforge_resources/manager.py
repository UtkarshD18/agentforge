import threading
from pydantic import BaseModel

class HardwareMetrics(BaseModel):
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    vram_bytes: int = 0
    ram_bytes: int = 0
    temperature: float = 0.0

class ResourceManager:
    def __init__(self, total_vram_bytes: int, total_ram_bytes: int) -> None:
        self.total_vram_bytes = total_vram_bytes
        self.total_ram_bytes = total_ram_bytes
        self.allocated_vram_bytes = 0
        self.allocated_ram_bytes = 0
        self._lock = threading.Lock()

    def get_hardware_metrics(self) -> HardwareMetrics:
        with self._lock:
            return HardwareMetrics(
                cpu_usage=15.0,
                gpu_usage=25.0,
                vram_bytes=self.allocated_vram_bytes,
                ram_bytes=self.allocated_ram_bytes,
                temperature=55.0
            )

    def allocate_vram(self, amount_bytes: int) -> bool:
        with self._lock:
            if self.allocated_vram_bytes + amount_bytes <= self.total_vram_bytes:
                self.allocated_vram_bytes += amount_bytes
                return True
            return False

    def release_vram(self, amount_bytes: int) -> None:
        with self._lock:
            self.allocated_vram_bytes = max(0, self.allocated_vram_bytes - amount_bytes)
