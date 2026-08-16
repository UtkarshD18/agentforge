import os
import threading
from typing import Dict, Any, Optional
from pydantic import BaseModel
from agentforge_hardware.discovery import discover_hardware_capabilities
from agentforge_hardware.monitor import get_gpu_metrics

class HardwareMetrics(BaseModel):
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    vram_bytes: int = 0
    ram_bytes: int = 0
    temperature: float = 0.0

class ResourceManager:
    def __init__(self, safety_ceiling_bytes: Optional[int] = None, headroom_bytes: int = 2 * 1024 * 1024 * 1024) -> None:
        self.headroom_bytes = headroom_bytes
        self._lock = threading.Lock()
        
        # Discover hardware capabilities
        caps = discover_hardware_capabilities()
        self.total_ram_bytes = caps.total_ram_bytes
        
        if caps.gpus:
            # Use the primary GPU
            primary_gpu = caps.gpus[0]
            self.gpu_index = primary_gpu.index
            self.total_vram_bytes = primary_gpu.total_vram_bytes
            self.has_gpu = True
        else:
            self.gpu_index = 0
            self.total_vram_bytes = 8 * 1024 * 1024 * 1024  # Fallback to 8GB mock VRAM
            self.has_gpu = False
            
        if safety_ceiling_bytes is not None:
            self.safety_ceiling_bytes = safety_ceiling_bytes
        else:
            self.safety_ceiling_bytes = max(0, self.total_vram_bytes - self.headroom_bytes)
            
        self.allocated_vram_bytes = 0
        self.allocated_ram_bytes = 0
        self.active_allocations: Dict[str, int] = {}

    def get_hardware_metrics(self) -> HardwareMetrics:
        with self._lock:
            cpu_usage = 15.0  # Default fallback
            gpu_usage = 0.0
            temp = 45.0
            
            if self.has_gpu:
                metrics = get_gpu_metrics(self.gpu_index)
                if metrics:
                    gpu_usage = metrics.gpu_utilization_percent
                    temp = metrics.temperature_celsius
                    
            return HardwareMetrics(
                cpu_usage=cpu_usage,
                gpu_usage=gpu_usage,
                vram_bytes=self.allocated_vram_bytes,
                ram_bytes=self.allocated_ram_bytes,
                temperature=temp
            )

    def can_fit(self, requirement_bytes: int) -> bool:
        with self._lock:
            return self.allocated_vram_bytes + requirement_bytes <= self.safety_ceiling_bytes

    def allocate_vram(self, amount_bytes: int) -> bool:
        with self._lock:
            if self.allocated_vram_bytes + amount_bytes <= self.safety_ceiling_bytes:
                self.allocated_vram_bytes += amount_bytes
                return True
            return False

    def release_vram(self, amount_bytes: int) -> None:
        with self._lock:
            self.allocated_vram_bytes = max(0, self.allocated_vram_bytes - amount_bytes)

    def reserve(self, model: str, amount_bytes: int) -> bool:
        with self._lock:
            if self.allocated_vram_bytes + amount_bytes <= self.safety_ceiling_bytes:
                self.allocated_vram_bytes += amount_bytes
                self.active_allocations[model] = amount_bytes
                return True
            return False

    def release(self, model: str) -> None:
        with self._lock:
            if model in self.active_allocations:
                amount = self.active_allocations.pop(model)
                self.allocated_vram_bytes = max(0, self.allocated_vram_bytes - amount)
