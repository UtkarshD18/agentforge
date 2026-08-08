import time
import pytest
from agentforge_core.di import get_container
from agentforge_core.events import Event, get_event_bus
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository
from agentforge_core.workflow import Artifact
from agentforge_execution import (
    ExecutionEngine,
    TaskTimeoutError,
    TaskCancelledError,
    ArtifactCache,
    execution_span,
    get_active_span_uri,
    ExecutionLineageTracker
)

def test_engine_retries_and_failure():
    engine = ExecutionEngine()
    
    task_log = []
    def fail_action():
        task_log.append("fail")
        raise ValueError("Simulated Task Crash")

    # Run task and expect it to fail after 3 retries
    with pytest.raises(ValueError) as exc_info:
        engine.run_task(
            task_uri="task://job-1/fail_task",
            action=fail_action,
            max_retries=3,
            timeout_seconds=2.0
        )
    assert "Simulated Task Crash" in str(exc_info.value)
    # Action should have been tried 3 times
    assert len(task_log) == 3

def test_engine_timeout():
    engine = ExecutionEngine()
    
    def slow_action():
        time.sleep(0.5)
        return "too-slow"
        
    with pytest.raises(TaskTimeoutError) as exc_info:
        engine.run_task(
            task_uri="task://job-1/slow_task",
            action=slow_action,
            max_retries=1,
            timeout_seconds=0.1
        )
    assert "timed out after" in str(exc_info.value)

def test_engine_cancellation():
    engine = ExecutionEngine()
    engine.cancel_task("task://job-1/cancelled_task")
    
    called = False
    def action():
        nonlocal called
        called = True
        return "success"
        
    with pytest.raises(TaskCancelledError) as exc_info:
        engine.run_task(
            task_uri="task://job-1/cancelled_task",
            action=action
        )
    assert "was cancelled by user" in str(exc_info.value)
    assert called is False

def test_artifact_caching():
    cache = ArtifactCache()
    inputs = {"video_file": "clip.mp4", "crop_aspect": "9:16"}
    checksum = cache.generate_checksum(inputs)
    
    artifact = Artifact(
        uri="artifact://cache/123",
        job_uri="job://session-1/j1",
        task_uri="task://j1/t1",
        type="video",
        data={"path": "processed.mp4"}
    )
    
    # Check cache miss
    assert cache.get_cached_artifact(checksum, "1.0") is None
    
    # Store and hit cache
    cache.set_cached_artifact(checksum, "1.0", artifact)
    cached = cache.get_cached_artifact(checksum, "1.0")
    assert cached is not None
    assert cached.uri == "artifact://cache/123"
    assert cached.data["path"] == "processed.mp4"

def test_telemetry_lineage_tracing():
    container = get_container()
    container.clear()
    
    repo = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, repo)
    
    parent_uri = "task://parent"
    child_uri = "task://child"
    
    with execution_span(parent_uri) as p_span:
        assert get_active_span_uri() == parent_uri
        
        with execution_span(child_uri) as c_span:
            assert get_active_span_uri() == child_uri
            
    # Active span should return to None outside contexts
    assert get_active_span_uri() is None
    
    # Retrieve persistent trace lineage tree from DB
    trace = ExecutionLineageTracker.get_lineage_trace(parent_uri)
    assert trace["uri"] == parent_uri
    assert len(trace["children"]) == 1
    assert trace["children"][0]["uri"] == child_uri
