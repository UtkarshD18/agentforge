import os
import tempfile
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from agentforge_eventbus import EventBus, ExecutionEvent, ExecutionEventType, EventStore
from agentforge_state import TaskStateStore, WorkerStateStore, ProjectStateStore
from agentforge_scheduler import TaskGraph, TaskNode, PlacementEngine, WorkerSelector, ProviderSelector
from agentforge_orchestrator import ExecutionOrchestrator
from agentforge_runtime_engine import TaskRunner, ExecutionUnit, ExecutionResponse, ArtifactResult, GraphResult
from agentforge_resources import ResourceManager, ModelManager, MemoryPlanner
from agentforge_plugins import PluginRegistry, PluginType, CapabilityManifest, WorkerRequirements
from agentforge_project import Project, ProjectSettings, ProjectGraph
from agentforge_hosts import HostCommand, HostCapabilities, HostAdapter
from agentforge_providers import CapabilityProvider, ProviderHealth

# 1. Mock Host Adapter
class MockResolveAdapter(HostAdapter):
    def __init__(self) -> None:
        self.commands_executed: List[HostCommand] = []

    def get_host_name(self) -> str:
        return "resolve"

    def get_capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            supports_timeline=True,
            supports_layers=False,
            supports_markers=True,
            supports_effects=True,
            supports_rendering=True,
            supports_undo=True
        )

    def execute_command(self, command: HostCommand) -> bool:
        self.commands_executed.append(command)
        return True

# 2. Mock Capability Provider
class MockWhisperProvider(CapabilityProvider):
    def execute(self, unit: ExecutionUnit, context: Any) -> ExecutionResponse:
        return ExecutionResponse(
            status="completed",
            results=[
                ArtifactResult(
                    result_id="res-1",
                    artifact_uri="artifact://transcript.json",
                    checksum="sha256-abcdef"
                )
            ]
        )

    def get_health(self) -> ProviderHealth:
        return ProviderHealth(latency_ms=120.0, availability=1.0)

# 3. Simple Mock Registry
class MockProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, CapabilityProvider] = {}

    def register_provider(self, capability: str, provider: CapabilityProvider) -> None:
        self._providers[capability] = provider

    def get_provider_for_capability(self, capability: str) -> Optional[CapabilityProvider]:
        return self._providers.get(capability)

def test_capability_kernel_vertical_slice() -> None:
    # A. Setup EventBus and EventStore
    temp_dir = tempfile.mkdtemp()
    store_file = os.path.join(temp_dir, "event_store.log")
    event_store = EventStore(store_file)
    event_bus = EventBus()

    events_published: List[ExecutionEvent] = []
    def log_event(event: Any) -> None:
        if isinstance(event, ExecutionEvent):
            events_published.append(event)
            event_store.append(event)

    event_bus.subscribe(log_event)

    # B. Setup State Stores
    task_store = TaskStateStore()
    worker_store = WorkerStateStore()
    project_store = ProjectStateStore()

    # Register Mock Worker
    worker_profile = {"worker_id": "gpu-0", "labels": ["nvidia", "cuda"]}
    worker_store.register_worker("gpu-0", worker_profile)

    # C. Setup Project
    proj = Project(
        project_id="proj-123",
        name="Nike Reel",
        settings=ProjectSettings(),
        graphs=ProjectGraph(
            media_graph_uri="db://media",
            execution_graph_uri="db://exec",
            knowledge_graph_uri="db://knowledge",
            workspace_graph_uri="db://workspace"
        )
    )
    project_store.set_project("proj-123", proj.model_dump())

    # D. Setup Resources
    resource_mgr = ResourceManager(safety_ceiling_bytes=6 * 1024 * 1024 * 1024)
    model_mgr = ModelManager(resource_mgr)
    memory_planner = MemoryPlanner(resource_mgr, model_mgr)

    # Acquire model reservation
    reservation = memory_planner.acquire_reservation("whisper-large", 2 * 1024 * 1024 * 1024)
    assert reservation is not None
    assert reservation.active is True
    assert resource_mgr.allocated_vram_bytes == 2 * 1024 * 1024 * 1024

    # E. Setup Providers & Plugins
    plugin_reg = PluginRegistry()
    manifest = CapabilityManifest(
        id="provider.whisper",
        name="Local Whisper",
        type="provider",
        requires=[],
        produces=["speech.transcription"],
        worker_requirements=WorkerRequirements(labels=["nvidia"])
    )
    plugin_reg.register_plugin(PluginType.PROVIDER, "provider.whisper", MockWhisperProvider(), manifest)

    prov_reg = MockProviderRegistry()
    prov_reg.register_provider("speech.transcription", MockWhisperProvider())

    # F. Setup Host Registry
    resolve_host = MockResolveAdapter()
    assert resolve_host.get_host_name() == "resolve"

    # G. Compile TaskGraph
    task_a = TaskNode(
        task_id="task-transcribe",
        capability="speech.transcription",
        status="queued",
        children=["task-update-timeline"]
    )
    task_b = TaskNode(
        task_id="task-update-timeline",
        capability="timeline.edit",
        status="queued",
        parents=["task-transcribe"]
    )
    graph = TaskGraph(
        execution_id="exec-456",
        nodes={"task-transcribe": task_a, "task-update-timeline": task_b},
        root_tasks=["task-transcribe"],
        leaf_tasks=["task-update-timeline"]
    )

    # H. Run Orchestrator
    runner = TaskRunner(prov_reg)
    orchestrator = ExecutionOrchestrator(
        scheduler=None,
        state_store=task_store,
        event_store=event_store,
        runtime=runner
    )

    # Publish start event
    start_event = ExecutionEvent(
        event_type=ExecutionEventType.TASK_STARTED,
        task_id="task-transcribe",
        payload={"msg": "Starting Transcription slice"}
    )
    event_bus.publish(start_event)

    # Run the DAG
    orchestrator.run_graph(graph)

    # Verify states in task store
    transcribe_state = task_store.get_task_state("task-transcribe")
    assert transcribe_state is not None
    assert transcribe_state["status"] == "completed"

    timeline_state = task_store.get_task_state("task-update-timeline")
    assert timeline_state is not None
    assert timeline_state["status"] == "completed"

    # Verify EventStore has persisted events
    persisted_events = event_store.read_all()
    assert len(persisted_events) > 0
    assert persisted_events[0]["event_type"] == "task.started"

    # Release VRAM reservation
    memory_planner.release_reservation(reservation)
    assert resource_mgr.allocated_vram_bytes == 0

    # Cleanup temp directory
    try:
        os.remove(store_file)
        os.rmdir(temp_dir)
    except OSError:
        pass
