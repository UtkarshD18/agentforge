from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class TaskNode(BaseModel):
    task_id: str
    capability: str
    status: str = "queued"
    priority: int = 10
    worker_id: Optional[str] = None
    parents: List[str] = Field(default_factory=list)
    children: List[str] = Field(default_factory=list)
    retry_count: int = 0
    artifacts: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)

class TaskGraph(BaseModel):
    execution_id: str
    nodes: Dict[str, TaskNode] = Field(default_factory=dict)
    root_tasks: List[str] = Field(default_factory=list)
    leaf_tasks: List[str] = Field(default_factory=list)
