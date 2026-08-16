import threading
from enum import Enum
from typing import Dict, Any, List

class ModelLifecycleState(str, Enum):
    DOWNLOADED = "downloaded"
    VERIFIED = "verified"
    LOADED = "loaded"
    PINNED = "pinned"
    EVICTED = "evicted"

class ModelManager:
    def __init__(self, resource_manager: Any) -> None:
        self.resource_manager = resource_manager
        self.active_models: Dict[str, ModelLifecycleState] = {}
        self.model_vram: Dict[str, int] = {}
        self.loaded_order: List[str] = []
        self._lock = threading.Lock()

    def load_model(self, model_name: str, required_vram: int) -> bool:
        with self._lock:
            # 1. Already loaded or pinned
            state = self.active_models.get(model_name)
            if state in (ModelLifecycleState.LOADED, ModelLifecycleState.PINNED):
                if model_name in self.loaded_order:
                    self.loaded_order.remove(model_name)
                self.loaded_order.append(model_name)  # Move to most recently used
                return True
                
            # 2. Dynamic LRU eviction cycle if required VRAM exceeds safety ceiling
            while self.resource_manager.allocated_vram_bytes + required_vram > self.resource_manager.safety_ceiling_bytes:
                evicted_any = False
                for m in list(self.loaded_order):
                    # Check if model can be evicted (is LOADED but NOT PINNED)
                    if self.active_models.get(m) == ModelLifecycleState.LOADED:
                        self._unload_model_unlocked(m)
                        evicted_any = True
                        break  # Break to re-evaluate remaining VRAM space
                if not evicted_any:
                    # No more evictable models, yet VRAM ceiling is exceeded
                    return False
                    
            # 3. Reserve and load
            if self.resource_manager.reserve(model_name, required_vram):
                self.active_models[model_name] = ModelLifecycleState.LOADED
                self.model_vram[model_name] = required_vram
                self.loaded_order.append(model_name)
                return True
            return False

    def unload_model(self, model_name: str) -> None:
        with self._lock:
            self._unload_model_unlocked(model_name)

    def _unload_model_unlocked(self, model_name: str) -> None:
        if model_name in self.loaded_order:
            self.loaded_order.remove(model_name)
        if model_name in self.active_models:
            self.resource_manager.release(model_name)
            self.active_models[model_name] = ModelLifecycleState.EVICTED

    def pin_model(self, model_name: str) -> None:
        with self._lock:
            if self.active_models.get(model_name) == ModelLifecycleState.LOADED:
                self.active_models[model_name] = ModelLifecycleState.PINNED

    def unpin_model(self, model_name: str) -> None:
        with self._lock:
            if self.active_models.get(model_name) == ModelLifecycleState.PINNED:
                self.active_models[model_name] = ModelLifecycleState.LOADED
