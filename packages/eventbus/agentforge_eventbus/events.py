import time
import uuid
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class Event(BaseModel):
    version: str = "1.0"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = Field(default_factory=dict)

class ExecutionEventType(str, Enum):
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    WORKER_SELECTED = "worker.selected"
    PROVIDER_SELECTED = "provider.selected"
    GRAPH_UPDATED = "graph.updated"
    ARTIFACT_CREATED = "artifact.created"
    MESSAGE = "message"
    WARNING = "warning"
    ERROR = "error"
    RESOURCE_UPDATE = "resource.update"

class ExecutionEvent(Event):
    event_type: ExecutionEventType
    task_id: Optional[str] = None
    worker_id: Optional[str] = None
