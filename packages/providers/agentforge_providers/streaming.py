from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from agentforge_core.fabric import CapabilityProvider, ModelConfig, ExecutionRequest, ExecutionResponse

class LayerStreamingProvider(CapabilityProvider, ABC):
    """
    Decoupled interface for incremental layer-by-layer weight streaming models.
    Can be optionally integrated with backends like AirLLM without introducing
    hard dependencies.
    """
    @abstractmethod
    def load_layers_incrementally(self, layer_indices: List[int]) -> None:
        """
        Loads only the specific model layers required into GPU VRAM.
        """
        pass

    @abstractmethod
    def release_layers(self) -> None:
        """
        Releases streamed layers to clear VRAM.
        """
        pass

    @abstractmethod
    def report_layer_memory(self) -> Dict[str, Any]:
        """
        Queries and returns VRAM size usage for the active loaded layers.
        """
        pass
