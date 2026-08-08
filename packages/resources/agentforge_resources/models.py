import threading
from enum import Enum
from typing import Dict, Any

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
        self._lock = threading.Lock()

    def load_model(self, model_name: str, required_vram: int) -> bool:
        with self._lock:
            if self.active_models.get(model_name) == ModelLifecycleState.LOADED:
                return True
            if self.resource_manager.allocate_vram(required_vram):
                self.active_models[model_name] = ModelLifecycleState.LOADED
                self.model_vram[model_name] = required_vram
                return True
            return False

    def unload_model(self, model_name: str) -> None:
        with self._lock:
            if self.active_models.get(model_name) == ModelLifecycleState.LOADED:
                vram = self.model_vram.get(model_name, 0)
                self.resource_manager.release_vram(vram)
                self.active_models[model_name] = ModelLifecycleState.EVICTED
