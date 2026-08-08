import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field

from agentforge_core.di import get_container
from agentforge_core.events import Event, get_event_bus
from agentforge_core.storage import Entity, SQLiteGraphRepository, SQLiteEventRepository, GraphRepository, EventRepository

# --- WebSocket Broadcaster ---
class ConnectionManager:
    """
    Manages active WebSocket client connections for real-time event broadcasting.
    """
    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast(self, event: Event) -> None:
        """
        Sends the event data to all connected clients.
        """
        if not self.active_connections:
            return
        
        event_json = event.model_dump_json()
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(event_json)
            except Exception:
                disconnected.append(connection)
                
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Callback triggered on any Event Bus publish event
async def event_bus_broadcast_callback(event: Event) -> None:
    await manager.broadcast(event)

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    repo = SQLiteGraphRepository("agentforge.db")
    event_repo = SQLiteEventRepository("agentforge.db")
    
    # 2. Register storage and event bus in global DI container
    container = get_container()
    container.register(GraphRepository, repo)
    container.register(EventRepository, event_repo)
    
    # 3. Subscribe the WebSocket broadcaster callback to the Event Bus
    bus = get_event_bus()
    bus.subscribe(event_bus_broadcast_callback)
    
    # Publish startup event
    bus.publish(Event(
        event_type="system.startup",
        payload={"status": "running", "api_version": "1.0"}
    ))
    
    yield
    
    # --- Shutdown ---
    bus.publish(Event(
        event_type="system.shutdown",
        payload={"status": "stopped"}
    ))
    # Unsubscribe callback
    bus.unsubscribe(event_bus_broadcast_callback)
    container.clear()

# --- FastAPI App Definition ---
app = FastAPI(
    title="AgentForge Runtime OS Daemon",
    description="The core execution engine and event broker for AgentForge workflows.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Pydantic API Models ---
class WorkspaceCreateRequest(BaseModel):
    name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkspaceResponse(BaseModel):
    uri: str
    name: str
    metadata: Dict[str, Any]

# --- REST Endpoints (/api/v1/) ---
@app.post("/api/v1/workspace", response_model=WorkspaceResponse, status_code=201)
def create_workspace(req: WorkspaceCreateRequest):
    container = get_container()
    repo = container.resolve(GraphRepository)
    
    import uuid
    workspace_id = str(uuid.uuid4())
    uri = f"workspace://{workspace_id}"
    
    entity = Entity(
        uri=uri,
        type="workspace",
        metadata={"name": req.name, **req.metadata}
    )
    repo.save_entity(entity)
    
    # Publish event
    bus = get_event_bus()
    bus.publish(Event(
        event_type="workspace.created",
        payload={"workspace_uri": uri, "name": req.name}
    ))
    
    return WorkspaceResponse(
        uri=uri,
        name=req.name,
        metadata=entity.metadata
    )

@app.get("/api/v1/workspace/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: str):
    container = get_container()
    repo = container.resolve(GraphRepository)
    
    uri = f"workspace://{workspace_id}"
    entity = repo.get_entity(uri)
    if not entity or entity.type != "workspace":
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    return WorkspaceResponse(
        uri=entity.uri,
        name=entity.metadata.get("name", "Unnamed Workspace"),
        metadata=entity.metadata
    )

# --- Resolve Session Schema and Store ---
class ProjectMetadata(BaseModel):
    name: str

class TimelineMetadata(BaseModel):
    name: str
    fps: float
    start_frame: int
    end_frame: int
    clip_count: int

class ResolveSession(BaseModel):
    host: str = "resolve"
    connected: bool = True
    project: ProjectMetadata
    timeline: TimelineMetadata
    source: str = "resolve"
    updated_at: float

active_session: Dict[str, Any] = {
    "host": "resolve",
    "connected": False,
    "project": {"name": "No Active Project"},
    "timeline": {
        "name": "No Active Timeline",
        "fps": 0.0,
        "start_frame": 0,
        "end_frame": 0,
        "clip_count": 0
    },
    "source": "resolve",
    "updated_at": 0.0
}

@app.get("/api/v1/hosts/resolve/session", response_model=ResolveSession)
def get_resolve_session():
    return active_session

@app.post("/api/v1/hosts/resolve/session", response_model=ResolveSession)
def post_resolve_session(session: ResolveSession):
    global active_session
    active_session.update(session.model_dump())
    
    # Broadcast timeline changes to connected clients on the EventBus
    try:
        bus = get_event_bus()
        bus.publish(Event(
            event_type="host.resolve.timeline.changed",
            payload=active_session
        ))
    except Exception:
        pass
        
    return active_session


# --- WebSockets Endpoint (/ws/v1/) ---
@app.websocket("/ws/v1/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; discard incoming client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
