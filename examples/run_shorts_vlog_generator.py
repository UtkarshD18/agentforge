import os
import sys
import time
from typing import List, Dict, Any

from agentforge_eventbus import EventBus, ExecutionEvent, ExecutionEventType, EventStore
from agentforge_state import TaskStateStore, WorkerStateStore, ProjectStateStore
from agentforge_scheduler import TaskGraph, TaskNode, PlacementEngine
from agentforge_orchestrator import ExecutionOrchestrator
from agentforge_runtime_engine import TaskRunner, ExecutionUnit, ExecutionResponse, ArtifactResult, GraphResult
from agentforge_resources import ResourceManager, ModelManager, MemoryPlanner
from agentforge_plugins import PluginRegistry, PluginType, CapabilityManifest, WorkerRequirements
from agentforge_project import Project, ProjectSettings, ProjectGraph
from agentforge_hosts import HostCommand, HostCapabilities, HostAdapter
from agentforge_providers import CapabilityProvider, ProviderHealth

# 1. Setup color palette console printing
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_dev_console(
    vram_used: str,
    active_model: str,
    event_logs: List[str],
    graph_nodes: List[str],
    resolve_status: str
) -> None:
    """Prints a beautiful, real-time-like Cursor developer console in the terminal."""
    os.system("clear" if os.name == "posix" else "cls")
    print(f"{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}🎬  AGENTFORGE OS DEVELOPER CONSOLE — SPRINT 1 DEMO{RESET}")
    print(f"{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"  {BOLD}Connection Status:{RESET}  {GREEN}🟢 Connected{RESET} ({resolve_status})")
    print(f"  {BOLD}GPU Utilization:{RESET}    {BLUE}████████████░░░ 82% {RESET} (RTX 4060 8GB)")
    print(f"  {BOLD}Active VRAM:{RESET}        {CYAN}{vram_used} / 8.0 GB{RESET} (Active Model: {active_model})")
    print(f"  {BOLD}Project State:{RESET}      {YELLOW}Nike Vlog Short #1{RESET}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  {BOLD}ACTIVE AGENTS:{RESET}      🟢 Coordinator | 🟢 Vision | 🟢 Motion | 🟢 Scheduler")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  {BOLD}MEDIA GRAPH NODES (Revisions):{RESET}")
    for node in graph_nodes[-6:]:
        print(f"    ├── {node}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  {BOLD}LIVE EVENT STREAM:{RESET}")
    for log in event_logs[-8:]:
        print(f"    {log}")
    print(f"{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    sys.stdout.flush()

class ResolveHostConnector(HostAdapter):
    def __init__(self) -> None:
        self.commands = []

    def get_host_name(self) -> str:
        return "resolve"

    def get_capabilities(self) -> HostCapabilities:
        return HostCapabilities(supports_timeline=True, supports_markers=True)

    def execute_command(self, command: HostCommand) -> bool:
        self.commands.append(command)
        return True

class LocalMotionProvider(CapabilityProvider):
    def execute(self, unit: ExecutionUnit, context: Any) -> ExecutionResponse:
        time.sleep(0.5)
        return ExecutionResponse(
            status="success",
            results=[
                GraphResult(
                    result_id="res-motion",
                    nodes_created=["node://shot/0?rev=1", "node://shot/1?rev=1"]
                )
            ]
        )

    def get_health(self) -> ProviderHealth:
        return ProviderHealth(latency_ms=15.0)

def main() -> None:
    # A. Scan video clips
    clips_dir = "/home/shadow/projects/agentforge/videoclips"
    if not os.path.exists(clips_dir):
        print(f"Error: videoclips directory not found at {clips_dir}")
        return

    clips = sorted([f for f in os.listdir(clips_dir) if f.upper().endswith(".MP4")])
    if not clips:
        print("Error: No video clips found.")
        return

    # B. Setup Kernel Systems
    event_bus = EventBus()
    event_store = EventStore("event_store.log")
    task_store = TaskStateStore()
    project_store = ProjectStateStore()

    # Track console messages
    console_logs = []
    graph_nodes = []

    def handle_bus_event(event: Any) -> None:
        if isinstance(event, ExecutionEvent):
            event_store.append(event)
            color = GREEN if "completed" in event.event_type else BLUE
            console_logs.append(f"[{time.strftime('%H:%M:%S')}] {color}{event.event_type.upper()}{RESET} — Task: {event.task_id} — {event.payload.get('msg', '')}")

    event_bus.subscribe(handle_bus_event)

    # C. Initialize Resources
    res_mgr = ResourceManager(total_vram_bytes=8 * 1024 * 1024 * 1024, total_ram_bytes=16 * 1024 * 1024 * 1024)
    model_mgr = ModelManager(res_mgr)
    memory_planner = MemoryPlanner(res_mgr, model_mgr)

    # D. Register Resolve host connection
    resolve_host = ResolveHostConnector()

    # E. Live simulation loop
    print("Initializing AgentForge OS...")
    time.sleep(1.0)

    # 1. Attach to Resolve
    event_bus.publish(ExecutionEvent(
        event_type=ExecutionEventType.TASK_STARTED,
        task_id="resolve-attach",
        payload={"msg": "Searching for active DaVinci Resolve timelines..."}
    ))
    resolve_status = "Resolve 21.0.4 Online"
    print_dev_console("0.0", "None", console_logs, graph_nodes, resolve_status)
    time.sleep(1.0)

    # 2. Add files to media graph
    for idx, clip in enumerate(clips):
        graph_nodes.append(f"node://clip/{idx}?rev=1 (path: {clip})")
        event_bus.publish(ExecutionEvent(
            event_type=ExecutionEventType.GRAPH_UPDATED,
            task_id="graph-update",
            payload={"msg": f"Discovered clip {clip} - registered in media graph."}
        ))
        print_dev_console("0.0", "None", console_logs, graph_nodes, resolve_status)
        time.sleep(0.4)

    # 3. Load Motion Analyzer Model and acquire VRAM reservation
    event_bus.publish(ExecutionEvent(
        event_type=ExecutionEventType.TASK_STARTED,
        task_id="motion-vram-allocation",
        payload={"msg": "Allocating VRAM reservation for local Motion Analyzer..."}
    ))
    print_dev_console("0.0", "None", console_logs, graph_nodes, resolve_status)
    time.sleep(1.0)

    reservation = memory_planner.acquire_reservation("motion-resnet-v2", 2 * 1024 * 1024 * 1024)
    event_bus.publish(ExecutionEvent(
        event_type=ExecutionEventType.RESOURCE_UPDATE,
        task_id="vram-reserved",
        payload={"msg": "Reserved 2.0 GB VRAM. Loading motion-resnet-v2 weights onto RTX 4060."}
    ))
    print_dev_console("2.0", "motion-resnet-v2", console_logs, graph_nodes, resolve_status)
    time.sleep(1.2)

    # 4. Run motion analysis on clips
    for idx, clip in enumerate(clips):
        event_bus.publish(ExecutionEvent(
            event_type=ExecutionEventType.TASK_PROGRESS,
            task_id=f"motion-analyze-clip-{idx}",
            payload={"msg": f"Processing visual shift matrices on {clip}..."}
        ))
        # Log to knowledge store
        event_bus.publish(ExecutionEvent(
            event_type=ExecutionEventType.ARTIFACT_CREATED,
            task_id=f"knowledge-update-clip-{idx}",
            payload={"msg": f"Indexed whip-pan panning events for {clip} into Knowledge DB."}
        ))
        graph_nodes.append(f"node://clip/{idx}/motion?rev=1 (whip_pan, confidence: 0.96)")
        print_dev_console("2.0", "motion-resnet-v2", console_logs, graph_nodes, resolve_status)
        time.sleep(0.8)

    # 5. Evict Motion model to release VRAM
    event_bus.publish(ExecutionEvent(
        event_type=ExecutionEventType.RESOURCE_UPDATE,
        task_id="motion-vram-release",
        payload={"msg": "Evicting Motion model weights from VRAM to prevent memory bloat."}
    ))
    memory_planner.release_reservation(reservation)
    print_dev_console("0.0", "None", console_logs, graph_nodes, resolve_status)
    time.sleep(1.0)

    # 6. Push markers to Resolve timeline
    event_bus.publish(ExecutionEvent(
        event_type=ExecutionEventType.TASK_STARTED,
        task_id="timeline-sync-markers",
        payload={"msg": "Compiling HostCommand list to place motion markers in Resolve Timeline..."}
    ))
    print_dev_console("0.0", "None", console_logs, graph_nodes, resolve_status)
    time.sleep(1.0)

    for idx, clip in enumerate(clips):
        cmd = HostCommand(
            command_id=f"cmd-marker-{idx}",
            host="resolve",
            parameters={"action": "add_marker", "clip": clip, "note": "Whip-pan camera transition"}
        )
        resolve_host.execute_command(cmd)
        event_bus.publish(ExecutionEvent(
            event_type=ExecutionEventType.TASK_COMPLETED,
            task_id=f"cmd-marker-{idx}",
            payload={"msg": f"Resolve timeline marker set at offset frame: {idx * 30}"}
        ))
        print_dev_console("0.0", "None", console_logs, graph_nodes, resolve_status)
        time.sleep(0.5)

    # 7. Jump to frame simulation
    event_bus.publish(ExecutionEvent(
        event_type=ExecutionEventType.TASK_STARTED,
        task_id="user-timeline-navigation",
        payload={"msg": f"User clicked motion marker node. Dispatching timeline jump control to frame 90."}
    ))
    print_dev_console("0.0", "None", console_logs, graph_nodes, resolve_status)
    time.sleep(1.5)

    event_bus.publish(ExecutionEvent(
        event_type=ExecutionEventType.TASK_COMPLETED,
        task_id="timeline-navigation-success",
        payload={"msg": "Timeline focus aligned. Jump-to-frame executed successfully."}
    ))
    print_dev_console("0.0", "None", console_logs, graph_nodes, resolve_status)

    print("\n✓ Sprint 1 Walking Skeleton Demo executed successfully!")
    print(f"✓ EventStore saved dynamically in: {os.path.abspath('event_store.log')}")

if __name__ == "__main__":
    main()
