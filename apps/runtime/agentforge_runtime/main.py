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

async def event_bus_broadcast_callback(event: Event) -> None:
    await manager.broadcast(event)


# --- AI Edit Planning Schemas ---
from typing import Literal, Optional, Union

class EditOperation(BaseModel):
    type: Literal["select_segment", "add_marker", "propose_trim", "insert_clip", "trim_clip", "add_title"]
    clip_id: str = Field(description="The exact filename of the clip")
    start_frame: int = Field(default=0, description="Clip relative start frame")
    end_frame: int = Field(default=0, description="Clip relative end frame")
    source_start: Optional[int] = Field(default=None)
    source_end: Optional[int] = Field(default=None)
    timeline_position: Optional[int] = Field(default=None)
    reason: str = Field(description="Explanation of the edit action")

class EditPlan(BaseModel):
    plan_id: str
    goal: str
    source: Literal["gemini", "deterministic_fallback"]
    timeline: Dict[str, str]
    operations: List[EditOperation]

class GenerateEditPlanRequest(BaseModel):
    goal: str

class ApplyEditPlanRequest(BaseModel):
    plan_id: str
    mode: Literal["preview", "apply"] = "apply"

active_edit_plans: Dict[str, EditPlan] = {}

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
    
    def persist_event_callback(event: Event) -> None:
        try:
            event_repo.log_event(
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                payload=event.payload,
                version=event.version
            )
        except Exception:
            pass
            
    bus.subscribe(persist_event_callback)
    
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
    # Unsubscribe callbacks
    bus.unsubscribe(event_bus_broadcast_callback)
    bus.unsubscribe(persist_event_callback)
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


@app.post("/api/v1/hosts/resolve/commands/test-control")
def run_test_control():
    from agentforge_hosts import HostCommand, ResolveHostAdapter
    adapter = ResolveHostAdapter()
    command = HostCommand(
        command_id="test-control",
        host="resolve"
    )
    success = adapter.execute_command(command)
    results = command.parameters.get("results", {})
    error = command.parameters.get("error", None)
    
    if not success and error:
        raise HTTPException(status_code=500, detail=error)
        
    return {
        "success": success,
        "steps": results
    }


@app.post("/api/v1/hosts/resolve/commands/analyze-timeline")
def run_analyze_timeline():
    import os
    from agentforge_hosts import ResolveHostAdapter
    from agentforge_analyzers import MotionAnalyzer
    from agentforge_core.mediagraph import MediaGraphRepository, TemporalNode, MediaNodeProvenance
    from agentforge_core.events import Event, get_event_bus
    
    adapter = ResolveHostAdapter()
    clips = adapter.get_timeline_clips()
    if not clips:
        return {
            "success": True,
            "clips_analyzed": []
        }
        
    analyzer = MotionAnalyzer(threshold=0.5)
    media_graph_repo = MediaGraphRepository()
    graph_uri = "graph://video/resolve-timeline"
    
    # Save the root MediaGraph entity to satisfy SQLite foreign key constraints
    from agentforge_core.storage import GraphRepository, Entity
    container = get_container()
    db_repo = container.resolve(GraphRepository)
    if not db_repo.get_entity(graph_uri):
        db_repo.save_entity(Entity(uri=graph_uri, type="media_graph"))
        
    analyzed_results = []
    
    for idx, clip in enumerate(clips):
        file_path = clip["file_path"]
        clip_name = clip["name"]
        fps = clip["fps"]
        timeline_start = clip["timeline_start_frame"]
        clip_start = clip["start_frame"]
        clip_duration = clip["duration"]
        left_offset = clip["left_offset"]
        
        motion_events = []
        if os.path.exists(file_path):
            raw_events = analyzer.analyze_clip(file_path, fps=fps)
            
            for s_idx, ev in enumerate(raw_events):
                ev_start_frame = ev["start_frame"]
                ev_end_frame = ev["end_frame"]
                
                # Check if visible within boundaries
                visible_start = max(ev_start_frame, left_offset)
                visible_end = min(ev_end_frame, left_offset + clip_duration)
                
                if visible_start < visible_end:
                    marker_offset = int((clip_start - timeline_start) + (visible_start - left_offset))
                    
                    # Create marker in Resolve via HostAdapter
                    note = f"{ev['direction'].capitalize()} camera movement\nconfidence: {ev['confidence']:.2f}"
                    adapter.add_marker(
                        marker_offset,
                        "Green",
                        "MOTION",
                        note,
                        "agentforge-motion-event"
                    )
                    
                    # Save node in MediaGraph
                    clean_name = clip_name.replace(".", "_")
                    node_uri = f"node://clip/{clean_name}/motion/{s_idx}?rev=1"
                    node = TemporalNode(
                        uri=node_uri,
                        provenance=MediaNodeProvenance(
                            created_by="motion-v1",
                            confidence=ev["confidence"]
                        ),
                        start_seconds=round(visible_start / fps, 2),
                        end_seconds=round(visible_end / fps, 2),
                        metadata={
                            "type": "motion",
                            "clip": clip_name,
                            "start_frame": int(visible_start),
                            "end_frame": int(visible_end),
                            "direction": ev["direction"],
                            "magnitude": ev["magnitude"],
                            "analyzer": "motion-v1"
                        }
                    )
                    media_graph_repo.save_node(graph_uri, node)
                    
                    # Publish Event to EventBus
                    try:
                        bus = get_event_bus()
                        bus.publish(Event(
                            event_type="graph.node.added",
                            payload={
                                "uri": node_uri,
                                "clip": clip_name,
                                "direction": ev["direction"],
                                "timeline_frame": marker_offset
                            }
                        ))
                    except Exception:
                        pass
                        
                    motion_events.append({
                        "direction": ev["direction"],
                        "start_frame": int(visible_start),
                        "end_frame": int(visible_end),
                        "confidence": ev["confidence"],
                        "timeline_frame": marker_offset
                    })
                    
        analyzed_results.append({
            "name": clip_name,
            "status": "success" if os.path.exists(file_path) else "file_not_found",
            "motion_events": motion_events
        })
        
    return {
        "success": True,
        "clips_analyzed": analyzed_results
    }


@app.post("/api/v1/hosts/resolve/commands/generate-edit-plan")
def generate_edit_plan(req_payload: GenerateEditPlanRequest):
    goal = req_payload.goal
    
    # 1. Retrieve active timeline clips
    from agentforge_hosts import ResolveHostAdapter
    adapter = ResolveHostAdapter()
    clips = adapter.get_timeline_clips()
    if not clips:
        plan = EditPlan(
            plan_id="plan-empty",
            goal=goal,
            source="deterministic_fallback",
            timeline={"project": "Unknown", "timeline": "Unknown"},
            operations=[]
        )
        active_edit_plans[plan.plan_id] = plan
        return {
            "source": "deterministic_fallback",
            "reason": "no_clips_found",
            "plan": plan.model_dump()
        }
        
    project_name = "Unknown"
    timeline_name = "Unknown"
    resolve = adapter.connect_to_resolve()
    if resolve:
        try:
            pm = resolve.GetProjectManager()
            p = pm.GetCurrentProject()
            project_name = p.GetName()
            t = p.GetCurrentTimeline()
            timeline_name = t.GetName()
        except Exception:
            pass
            
    # 2. Retrieve motion events from database
    from agentforge_core.mediagraph import MediaGraphRepository
    media_graph_repo = MediaGraphRepository()
    nodes = media_graph_repo.get_graph_nodes("graph://video/resolve-timeline")
    
    motion_events_str = ""
    for node in nodes:
        meta = node.metadata
        if meta.get("type") == "motion":
            motion_events_str += f"- Clip: {meta.get('clip')} | Direction: {meta.get('direction')} | Magnitude: {meta.get('magnitude')} | Frames: {meta.get('start_frame')}-{meta.get('end_frame')}\n"
            
    # 3. Construct prompt
    prompt = f"""You are an expert video editor AI assistant integrated with DaVinci Resolve.
Goal: {goal}
Timeline: '{timeline_name}' in project '{project_name}'
Available clips on video track 1:
"""
    for clip in clips:
        prompt += f"- Name: {clip['name']} | Duration: {clip['duration']} frames | Path: {clip['file_path']}\n"
        
    if motion_events_str:
        prompt += f"\nDetected Motion Events in Media Graph:\n{motion_events_str}"
        
    prompt += """
Generate a structured edit plan to achieve the goal using ONLY the following operations:
- "select_segment": Jumps playhead to segment start.
- "add_marker": Places a Cyan anchor marker with cut explanation.
- "propose_trim": Places a Red boundary marker indicating crop boundaries.

Return ONLY a valid JSON object matching this schema. Do NOT wrap in codeblocks or markdown.
Schema:
{
  "plan_id": "unique-plan-string-id",
  "goal": "the user goal",
  "source": "gemini",
  "timeline": {"project": "project_name", "timeline": "timeline_name"},
  "operations": [
    {
      "type": "select_segment" | "add_marker" | "propose_trim",
      "clip_id": "exact clip name (e.g. IMG_0208.mov)",
      "start_frame": integer frame index relative to clip start,
      "end_frame": integer frame index relative to clip start,
      "reason": "reasoning notes"
    }
  ]
}
"""
    
    from agentforge_providers.google.provider import GoogleProvider
    from agentforge_core.fabric import AIRequest, AIMessage
    import os
    import json
    import uuid
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        fallback_ops = []
        for clip in clips:
            if "IMG_0208" in clip["name"]:
                fallback_ops.append(EditOperation(
                    type="select_segment",
                    clip_id=clip["name"],
                    start_frame=30,
                    end_frame=60,
                    reason="Strong panning motion from optical flow"
                ))
                fallback_ops.append(EditOperation(
                    type="propose_trim",
                    clip_id=clip["name"],
                    start_frame=0,
                    end_frame=30,
                    reason="Trim slow motion start segment"
                ))
            else:
                fallback_ops.append(EditOperation(
                    type="add_marker",
                    clip_id=clip["name"],
                    start_frame=10,
                    end_frame=10,
                    reason="Anchor edit point"
                ))
                
        plan = EditPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            goal=goal,
            source="deterministic_fallback",
            timeline={"project": project_name, "timeline": timeline_name},
            operations=fallback_ops
        )
        active_edit_plans[plan.plan_id] = plan
        return {
            "source": "deterministic_fallback",
            "reason": "gemini_unavailable",
            "plan": plan.model_dump()
        }
        
    try:
        provider = GoogleProvider()
        req = AIRequest(
            messages=[AIMessage(role="user", content=prompt)],
            model="gemini-2.5-flash"
        )
        res = provider.execute(req)
        clean_text = res.text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.splitlines()
            if lines[0].startswith("```json"):
                clean_text = "\n".join(lines[1:-1])
            elif lines[0].startswith("```"):
                clean_text = "\n".join(lines[1:-1])
                
        plan_dict = json.loads(clean_text)
        if not plan_dict.get("plan_id"):
            plan_dict["plan_id"] = f"plan-{uuid.uuid4().hex[:8]}"
        plan_dict["source"] = "gemini"
        plan_dict["timeline"] = {"project": project_name, "timeline": timeline_name}
        
        plan = EditPlan.model_validate(plan_dict)
        active_edit_plans[plan.plan_id] = plan
        return {
            "source": "gemini",
            "model": "gemini-2.5-flash",
            "plan": plan.model_dump()
        }
    except Exception as e:
        fallback_ops = [
            EditOperation(
                type="select_segment",
                clip_id=clips[0]["name"],
                start_frame=15,
                end_frame=45,
                reason="Primary motion focus"
            )
        ]
        plan = EditPlan(
            plan_id=f"plan-err-{uuid.uuid4().hex[:8]}",
            goal=goal,
            source="deterministic_fallback",
            timeline={"project": project_name, "timeline": timeline_name},
            operations=fallback_ops
        )
        active_edit_plans[plan.plan_id] = plan
        return {
            "source": "deterministic_fallback",
            "reason": f"gemini_failed: {str(e)}",
            "plan": plan.model_dump()
        }


@app.post("/api/v1/hosts/resolve/commands/apply-edit-plan")
def apply_edit_plan(req_payload: ApplyEditPlanRequest):
    plan_id = req_payload.plan_id
    mode = req_payload.mode
    
    if plan_id not in active_edit_plans:
        raise HTTPException(status_code=404, detail="Edit plan not found or already executed.")
        
    plan = active_edit_plans[plan_id]
    from agentforge_hosts import ResolveHostAdapter
    adapter = ResolveHostAdapter()
    
    if mode == "apply":
        # APPLY Mode: Real timeline clip assembly, trimming, and inspection
        result = adapter.build_timeline_from_edit_plan(
            [op.model_dump() for op in plan.operations],
            target_timeline_name="AgentForge_Vlog_Short_Test"
        )
        
        if result.get("success"):
            try:
                from agentforge_core.events import Event, get_event_bus
                get_event_bus().publish(Event(
                    event_type="execution.edit_plan.applied",
                    payload={
                        "plan_id": plan.plan_id,
                        "source": plan.source,
                        "mode": "apply",
                        "audit_results": result.get("audit_results")
                    }
                ))
            except Exception:
                pass
                
            del active_edit_plans[plan_id]
            return {
                "success": True,
                "plan_id": plan_id,
                "mode": "apply",
                "audit_results": result.get("audit_results")
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Edit builder execution failed."))
            
    else:
        # PREVIEW Mode: Markers only
        clips = adapter.get_timeline_clips()
        if not clips:
            raise HTTPException(status_code=400, detail="No timeline clips found to apply preview edit plan.")
            
        clip_map = {clip["name"]: clip for clip in clips}
        success_ops = []
        
        for op in plan.operations:
            clip_id = op.clip_id
            if clip_id not in clip_map:
                continue
                
            clip = clip_map[clip_id]
            success = adapter.apply_operation(op.model_dump(), clip)
            if success:
                success_ops.append(op.model_dump())
                
        try:
            from agentforge_core.events import Event, get_event_bus
            get_event_bus().publish(Event(
                event_type="execution.edit_plan.applied",
                payload={
                    "plan_id": plan.plan_id,
                    "source": plan.source,
                    "mode": "preview",
                    "operations_applied": success_ops
                }
            ))
        except Exception:
            pass
            
        del active_edit_plans[plan_id]
        return {
            "success": True,
            "plan_id": plan_id,
            "mode": "preview",
            "operations_applied": len(success_ops)
        }


@app.post("/api/v1/hosts/resolve/commands/reject-edit-plan")
def reject_edit_plan(req_payload: ApplyEditPlanRequest):
    plan_id = req_payload.plan_id
    if plan_id in active_edit_plans:
        del active_edit_plans[plan_id]
    return {"success": True}


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
