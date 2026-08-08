from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class WorkerRequirements(BaseModel):
    labels: List[str] = Field(default_factory=list)
    min_vram_bytes: int = 0
    min_ram_bytes: int = 0
    supports_streaming: bool = False
    preferred_devices: List[str] = Field(default_factory=list)

class CapabilityManifest(BaseModel):
    manifest_schema_version: str = "1.0"
    id: str
    name: str
    description: str = ""
    version: str = "1.0"
    type: str  # "analyzer", "provider", "host", "graph_builder", "agent"
    requires: List[str] = Field(default_factory=list)
    produces: List[str] = Field(default_factory=list)
    modalities: List[str] = Field(default_factory=list)
    hardware_requirements: Dict[str, Any] = Field(default_factory=dict)
    cost_tier: str = "low"
    priority: int = 10
    worker_requirements: WorkerRequirements = Field(default_factory=WorkerRequirements)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    minimum_sdk_version: str = "1.0"
    maximum_sdk_version: Optional[str] = None
