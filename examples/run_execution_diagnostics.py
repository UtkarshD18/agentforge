import time
from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository
from agentforge_core.workflow import Artifact
from agentforge_execution import (
    ExecutionEngine,
    ArtifactCache,
    execution_span,
    ExecutionLineageTracker
)

def main() -> None:
    print("==================================================")
    print("🚀 Running AgentForge Execution Engine Diagnostics")
    print("==================================================")

    # 1. Setup DI storage repo for trace span persistence
    repo = SQLiteGraphRepository(":memory:")
    container = get_container()
    container.register(GraphRepository, repo)
    print("✓ Persistent storage registered in DI Container.")

    engine = ExecutionEngine()
    cache = ArtifactCache()

    # 2. Trace nested execution span lineage tree
    print("\n[Trace Tree] Creating nested trace spans...")
    root_uri = "task://job-1/root"
    child1_uri = "task://job-1/transcribe"
    child2_uri = "task://job-1/scene_detect"
    
    with execution_span(root_uri):
        # Transcribe nested span
        with execution_span(child1_uri):
            time.sleep(0.02)
        # Scene detect nested span
        with execution_span(child2_uri):
            time.sleep(0.02)

    # Retrieve and print trace tree
    trace_tree = ExecutionLineageTracker.get_lineage_trace(root_uri)
    print(f"✓ Lineage Trace Tree resolved: {trace_tree['uri']}")
    for child in trace_tree["children"]:
        print(f"  └── child_span: {child['uri']}")

    # 3. Demonstrate Task Retry recovery
    print("\n[Retry Test] Executing task with transient failures...")
    attempts = 0
    def transient_action():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError(f"Database unavailable (attempt {attempts})")
        return "Task Complete (Success)"

    task_result = engine.run_task(
        task_uri="task://job-1/transient_db",
        action=transient_action,
        max_retries=3,
        timeout_seconds=5.0
    )
    print(f"✓ Task completed successfully after retries. Result: '{task_result}'")

    # 4. Demonstrate Checksum-Based Artifact Cache hits
    print("\n[Caching Test] Executing transcode task with artifact cache...")
    inputs = {"file": "source.mp4", "codec": "h264_nvenc", "resolution": "1080p"}
    checksum = cache.generate_checksum(inputs)
    version = "1.0"

    # Simulation check: Cache Miss
    cached = cache.get_cached_artifact(checksum, version)
    if cached is None:
        print("  - Cache Miss! Executing transcode logic...")
        # Simulate rendering output
        time.sleep(0.1)
        transcode_output = Artifact(
            uri="artifact://transcode/out-42",
            job_uri="job://job-1",
            task_uri="task://job-1/transcode",
            type="video",
            data={"path": "output_1080p.mp4", "size_bytes": 1024 * 512}
        )
        cache.set_cached_artifact(checksum, version, transcode_output)
        print(f"  - Output saved in Cache: {transcode_output.uri}")

    # Simulation check: Cache Hit
    print("  - Re-running identical transcode request...")
    cached_hit = cache.get_cached_artifact(checksum, version)
    if cached_hit is not None:
        print(f"✓ Cache Hit! Retained artifact from memory: {cached_hit.uri}")
        print(f"  - Cached file path: {cached_hit.data['path']}")

    print("==================================================")
    print("🎉 EXECUTION ENGINE DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
