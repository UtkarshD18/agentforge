from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    """
    Metadata capabilities profile for an AI model.
    """
    model_name: str
    capabilities: List[str]                  # e.g., ['text_generation', 'vision', 'embeddings']
    cost_tier: str = "medium"                # 'low', 'medium', 'high'
    local: bool = False                      # Local (Ollama) vs Cloud (Gemini)
    score: int = 80                          # Capability quality score (1-100)
    latency_seconds_est: float = 1.0
    active: bool = True

class ExecutionRequest(BaseModel):
    """
    Agnostic base class representing any request executed by the fabric.
    """
    task_type: str = "generic"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionTelemetry(BaseModel):
    """
    Standardized execution profiling metrics.
    """
    duration_seconds: float = 0.0
    device_used: str = "cpu"
    ram_usage_bytes: int = 0
    vram_usage_bytes: int = 0
    cache_hit: bool = False
    retry_count: int = 0

class ExecutionResponse(BaseModel):
    """
    Agnostic base class representing any response returned by the fabric.
    """
    success: bool = True
    telemetry: ExecutionTelemetry = Field(default_factory=ExecutionTelemetry)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class AIMessage(BaseModel):
    """
    Standardized chat message payload.
    """
    role: str                      # 'user', 'assistant', 'system'
    content: str

class AIRequest(ExecutionRequest):
    """
    Agnostic container payload to send to any provider model. Supports multimodal inputs.
    """
    task_type: str = "ai_generation"
    model: str
    messages: List[AIMessage]
    images: List[str] = Field(default_factory=list)      # Local file paths or URIs
    videos: List[str] = Field(default_factory=list)      # Local file paths or URIs
    audio: List[str] = Field(default_factory=list)       # Local file paths or URIs
    documents: List[str] = Field(default_factory=list)   # Local file paths or URIs
    temperature: float = 0.7
    max_tokens: int = 4096
    response_schema: Optional[Dict[str, Any]] = None

class AIResponseUsage(BaseModel):
    """
    Standardized token count and cost usage details.
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0

class AIResponse(ExecutionResponse):
    """
    Standardized structured response wrapper returned by any provider plugin.
    """
    text: str
    usage: AIResponseUsage = Field(default_factory=AIResponseUsage)
    finish_reason: str = "stop"    # 'stop', 'length', 'cancel', 'error'
    provider_name: str
    model_name: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)

class CapabilityProvider(ABC):
    """
    Base Abstract Class representing any capability execution target (AI models, code/compilers, local binaries).
    """
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def get_available_models(self) -> List[ModelConfig]:
        pass

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Executes a capability task based on the standardized request schema.
        """
        pass

class ExecutionFabric:
    """
    Thread-safe registry for Capability Providers and Model configuration mappings.
    Selects the optimal provider and model based on task capability needs.
    """
    def __init__(self) -> None:
        self._providers: Dict[str, CapabilityProvider] = {}
        import threading
        self._lock = threading.Lock()

    def register_provider(self, provider: CapabilityProvider) -> None:
        with self._lock:
            self._providers[provider.get_provider_name()] = provider

    def get_provider(self, name: str) -> Optional[CapabilityProvider]:
        with self._lock:
            return self._providers.get(name)

    def resolve_best_model(
        self,
        required_capabilities: List[str],
        prefer_local: bool = False,
        max_cost_tier: str = "high"
    ) -> Optional[Tuple[CapabilityProvider, str]]:
        """
        Scans all registered models to find the highest-scoring candidate
        that satisfies all required capabilities and fits the cost requirements.
        Returns a tuple of (Provider, model_name).
        """
        best_candidate: Optional[Tuple[CapabilityProvider, str]] = None
        best_score = -1

        # Mapping cost weights to assist evaluations
        cost_weight = {"low": 1, "medium": 2, "high": 3}
        max_cost_val = cost_weight.get(max_cost_tier.lower(), 3)

        with self._lock:
            for p_name, provider in self._providers.items():
                try:
                    models = provider.get_available_models()
                except Exception:
                    continue

                for m in models:
                    if not m.active:
                        continue
                    
                    # 1. Verify capabilities match
                    if not all(cap in m.capabilities for cap in required_capabilities):
                        continue

                    # 2. Verify cost parameters
                    m_cost_val = cost_weight.get(m.cost_tier.lower(), 2)
                    if m_cost_val > max_cost_val:
                        continue

                    # 3. Score evaluation (bonus if matching preferred local parameters)
                    final_score = m.score
                    if prefer_local and m.local:
                        final_score += 20  # Bias towards local execution
                    elif not prefer_local and not m.local:
                        final_score += 5   # Minor bias towards cloud reasoning

                    if final_score > best_score:
                        best_score = final_score
                        best_candidate = (provider, m.model_name)

        return best_candidate

class AudioTranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    confidence: float

class AudioTranscriptionRequest(ExecutionRequest):
    task_type: str = "audio_transcription"
    audio_path: str

class AudioTranscriptionResponse(ExecutionResponse):
    text: str
    segments: List[AudioTranscriptSegment]
