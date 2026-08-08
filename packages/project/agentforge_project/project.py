import time
from typing import Dict, Any
from pydantic import BaseModel, Field

class ProjectSettings(BaseModel):
    theme: str = "dark"
    resource_limits: Dict[str, Any] = Field(default_factory=dict)
    cost_limit: float = 10.0

class ProjectGraph(BaseModel):
    media_graph_uri: str
    execution_graph_uri: str
    knowledge_graph_uri: str
    workspace_graph_uri: str

class Project(BaseModel):
    project_id: str
    name: str
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    graphs: ProjectGraph
    created_at: float = Field(default_factory=time.time)
