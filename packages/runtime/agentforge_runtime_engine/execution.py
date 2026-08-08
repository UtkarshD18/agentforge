from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ExecutionUnit(BaseModel):
    unit_id: str
    capability: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True

class ExecutionResult(BaseModel):
    result_id: str
    kind: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class ArtifactResult(ExecutionResult):
    kind: str = "artifact"
    artifact_uri: str
    checksum: str

class GraphResult(ExecutionResult):
    kind: str = "graph"
    nodes_created: List[str] = Field(default_factory=list)

class ExecutionResponse(BaseModel):
    status: str = "success"
    results: List[ExecutionResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)

class TaskRunner:
    def __init__(self, provider_registry: Any) -> None:
        self.provider_registry = provider_registry

    def run_unit(self, unit: ExecutionUnit, context: Any) -> ExecutionResponse:
        provider = self.provider_registry.get_provider_for_capability(unit.capability)
        if not provider:
            return ExecutionResponse(
                status="failed",
                warnings=[f"No provider found for capability {unit.capability}"]
            )
        return provider.execute(unit, context)
