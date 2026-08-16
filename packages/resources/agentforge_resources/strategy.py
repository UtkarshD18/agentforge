import time
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

class InferenceStrategy(str, Enum):
    FULL_GPU = "full_gpu"
    QUANTIZED = "quantized"
    CPU_OFFLOAD = "cpu_offload"
    LAYER_STREAMING = "layer_streaming"
    CLOUD = "cloud"

class ModelCapabilityProfile(BaseModel):
    model_name: str
    min_vram_bytes: int
    local: bool = True
    quantization_options: List[str] = Field(default_factory=list) # e.g. ["4bit", "8bit"]
    cpu_offload_support: bool = False
    layer_streaming_support: bool = False
    capabilities: List[str] = Field(default_factory=list) # e.g. ["vision", "audio_transcription"]
    max_context_tokens: int = 4096
    expected_quality: float = 0.8  # scale from 0.0 to 1.0

class InferenceTelemetry(BaseModel):
    model: str
    strategy: InferenceStrategy
    vram_before: int = 0
    vram_peak: int = 0
    vram_after: int = 0
    ram_peak: int = 0
    load_time: float = 0.0
    inference_time: float = 0.0
    tokens_per_second: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    success: bool = True
    quality_score: float = 0.0

class StrategySelector:
    """
    Selects the optimal model execution strategy dynamically based on:
    - Task capabilities and priority
    - Model capability profiles
    - Live GPU VRAM metrics and system RAM availability
    - Multi-parameter cost function scoring
    """
    def __init__(self, profiles: List[ModelCapabilityProfile]) -> None:
        self.profiles = profiles

    def select_best_strategy(
        self,
        required_capabilities: List[str],
        live_free_vram: int,
        live_free_ram: int,
        latency_weight: float = 1.0,
        quality_weight: float = 1.0,
        memory_weight: float = 1.0,
        cost_weight: float = 1.0,
        is_interactive: bool = False
    ) -> Optional[Tuple[ModelCapabilityProfile, InferenceStrategy]]:
        best_candidate: Optional[Tuple[ModelCapabilityProfile, InferenceStrategy]] = None
        best_score = -999999.0
        
        # Boost latency sensitivity if interactive
        eff_latency_weight = latency_weight * 3.0 if is_interactive else latency_weight

        for profile in self.profiles:
            # 1. Match capability requirements
            if not all(cap in profile.capabilities for cap in required_capabilities):
                continue
                
            # 2. Score each strategy supported by the model
            strategies_to_evaluate = [InferenceStrategy.CLOUD]
            
            if profile.local:
                # FULL_GPU check
                if live_free_vram >= profile.min_vram_bytes:
                    strategies_to_evaluate.append(InferenceStrategy.FULL_GPU)
                    
                # QUANTIZED check
                if "4bit" in profile.quantization_options or "8bit" in profile.quantization_options:
                    quant_vram = int(profile.min_vram_bytes * 0.45)
                    if live_free_vram >= quant_vram:
                        strategies_to_evaluate.append(InferenceStrategy.QUANTIZED)
                        
                # CPU_OFFLOAD check
                if profile.cpu_offload_support:
                    gpu_base = int(profile.min_vram_bytes * 0.20)
                    cpu_needed = int(profile.min_vram_bytes * 0.85)
                    if live_free_vram >= gpu_base and live_free_ram >= cpu_needed:
                        strategies_to_evaluate.append(InferenceStrategy.CPU_OFFLOAD)
                        
                # LAYER_STREAMING check
                if profile.layer_streaming_support:
                    gpu_layer = int(profile.min_vram_bytes * 0.08)
                    if live_free_vram >= gpu_layer:
                        strategies_to_evaluate.append(InferenceStrategy.LAYER_STREAMING)

            for strategy in strategies_to_evaluate:
                # Estimate cost parameters
                if strategy == InferenceStrategy.FULL_GPU:
                    quality = profile.expected_quality
                    latency = 1.0
                    mem_pressure = float(profile.min_vram_bytes) / max(live_free_vram, 1)
                    monetary_cost = 0.0
                elif strategy == InferenceStrategy.QUANTIZED:
                    quality = profile.expected_quality - 0.05
                    latency = 1.2
                    mem_pressure = float(profile.min_vram_bytes * 0.45) / max(live_free_vram, 1)
                    monetary_cost = 0.0
                elif strategy == InferenceStrategy.CPU_OFFLOAD:
                    quality = profile.expected_quality
                    latency = 4.0
                    mem_pressure = float(profile.min_vram_bytes * 0.20) / max(live_free_vram, 1)
                    monetary_cost = 0.05
                elif strategy == InferenceStrategy.LAYER_STREAMING:
                    quality = profile.expected_quality
                    latency = 10.0  # streaming overhead penalty
                    mem_pressure = float(profile.min_vram_bytes * 0.08) / max(live_free_vram, 1)
                    monetary_cost = 0.10
                else:  # CLOUD
                    quality = 0.95
                    latency = 2.0  # network roundtrip
                    mem_pressure = 0.0
                    monetary_cost = 0.50

                # Score Function
                score = (
                    (quality_weight * quality)
                    - (eff_latency_weight * (latency / 10.0))  # normalize latency impact
                    - (memory_weight * mem_pressure)
                    - (cost_weight * monetary_cost)
                )
                
                if score > best_score:
                    best_score = score
                    best_candidate = (profile, strategy)
                    
        return best_candidate
