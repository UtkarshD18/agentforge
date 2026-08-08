import time
import pytest
from agentforge_core.di import get_container
from agentforge_core.events import Event, get_event_bus
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository, Entity
from agentforge_core.workflow import Job, Task, JobState, TaskState
from agentforge_core.scheduler import Scheduler

def test_scheduler_job_lifecycle():
    # Setup Container and Repositories
    container = get_container()
    container.clear()
    
    repo = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, repo)
    
    # Track Event Bus events
    events = []
    def track_events(e: Event):
        events.append(e)
    get_event_bus().subscribe(track_events)
    
    # Build Job & Tasks
    recipe = Entity(uri="recipe://hello-world", type="recipe", metadata={"name": "Hello World"})
    repo.save_entity(recipe)
    
    job = Job(uri="job://session-1/j1", workflow_uri="recipe://hello-world")
    tasks = [
        Task(uri="task://j1/t1", job_uri=job.uri, task_type="planner"),
        Task(uri="task://j1/t2", job_uri=job.uri, task_type="executor")
    ]
    
    # Submit Job
    scheduler = Scheduler()
    scheduler.submit_job(job, tasks)
    
    # Since scheduler runs on a background thread, we wait for completion
    timeout = 2.0
    start_time = time.time()
    while True:
        job_entity = repo.get_entity(job.uri)
        if job_entity and job_entity.metadata.get("state") == JobState.COMPLETED:
            break
        if time.time() - start_time > timeout:
            pytest.fail("Scheduler job execution timed out")
        time.sleep(0.05)
        
    get_event_bus().unsubscribe(track_events)
    
    # Verify DB States
    db_job = repo.get_entity(job.uri)
    assert db_job is not None
    assert db_job.metadata["state"] == JobState.COMPLETED
    
    db_t1 = repo.get_entity("task://j1/t1")
    assert db_t1 is not None
    assert db_t1.metadata["state"] == TaskState.COMPLETED
    
    db_t2 = repo.get_entity("task://j1/t2")
    assert db_t2 is not None
    assert db_t2.metadata["state"] == TaskState.COMPLETED
    
    # Verify Relationships (owns edges)
    related_tasks = repo.get_related_entities(job.uri, "owns")
    assert len(related_tasks) == 2
    
    # Verify Event sequence
    event_types = [e.event_type for e in events if e.correlation_id == job.uri]
    assert "job.queued" in event_types
    assert "job.started" in event_types
    assert "task.running" in event_types
    assert "task.completed" in event_types
    assert "job.completed" in event_types
