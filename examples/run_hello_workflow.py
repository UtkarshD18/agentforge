import time
from typing import Any, List
from agentforge_core.di import get_container
from agentforge_core.events import Event, get_event_bus
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository, Entity
from agentforge_core.workflow import Job, Task, JobState, TaskState
from agentforge_core.scheduler import Scheduler

def event_logger(event: Event) -> None:
    """
    Subscribed to Event Bus to print real-time state changes.
    """
    print(f"📡 [Event Bus Log] [{event.event_type}] payload: {event.payload}")

def main() -> None:
    print("==================================================")
    print("🚀 Starting AgentForge OS Mock Hello World Workflow")
    print("==================================================")

    # 1. Initialize core storage repository (using an in-memory SQLite for verification)
    repo = SQLiteGraphRepository(":memory:")
    
    # 2. Register storage inside global DI Container
    container = get_container()
    container.register(GraphRepository, repo)
    
    # 3. Subscribe event logger to the Event Bus
    bus = get_event_bus()
    bus.subscribe(event_logger)

    # 4. Save workflow recipe entity in DB (to prevent Foreign Key violations)
    recipe_uri = "recipe://hello-world"
    recipe = Entity(uri=recipe_uri, type="recipe", metadata={"name": "Hello World Workflow"})
    repo.save_entity(recipe)
    print(f"✓ Registered Workflow Recipe in DB: {recipe_uri}")

    # 5. Define Job and Tasks
    job_uri = "job://session-1/hello-job"
    job = Job(uri=job_uri, workflow_uri=recipe_uri)
    
    tasks = [
        Task(uri="task://hello-job/t-planner", job_uri=job_uri, task_type="planner"),
        Task(uri="task://hello-job/t-executor", job_uri=job_uri, task_type="executor")
    ]

    # 6. Submit Job to Scheduler
    print(f"✓ Submitting Job to Scheduler: {job_uri} containing {len(tasks)} tasks...")
    scheduler = Scheduler()
    scheduler.submit_job(job, tasks)

    # 7. Block main thread until the job executes and changes to COMPLETED state
    timeout = 3.0
    start_time = time.time()
    completed = False
    
    while time.time() - start_time < timeout:
        job_entity = repo.get_entity(job_uri)
        if job_entity and job_entity.metadata.get("state") == JobState.COMPLETED:
            completed = True
            break
        time.sleep(0.1)

    # 8. Unsubscribe logger and print final report
    bus.unsubscribe(event_logger)
    
    print("==================================================")
    if completed:
        print("🎉 Verification SUCCESS!")
        print(f"Job URI: {job_uri}")
        print("Tasks Verified:")
        for t in tasks:
            t_entity = repo.get_entity(t.uri)
            status = t_entity.metadata.get("state") if t_entity else "Not Found"
            print(f"  - {t.uri} [{status}]")
    else:
        print("❌ Verification FAILED or timed out.")
    print("==================================================")

if __name__ == "__main__":
    main()
