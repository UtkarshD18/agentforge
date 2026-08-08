import time
import threading
from typing import List
from agentforge_core.di import get_container
from agentforge_core.events import Event, get_event_bus
from agentforge_core.storage import GraphRepository, Entity
from agentforge_core.workflow import Job, Task, JobState, TaskState

class Scheduler:
    """
    Core Scheduler executing Job workflows sequentially in background threads.
    Coordinates database state updates and publishes lifecycle events to the Event Bus.
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def submit_job(self, job: Job, tasks: List[Task]) -> None:
        """
        Registers the Job and Tasks in database, changes state to QUEUED,
        and dispatches a background worker thread to process execution.
        """
        container = get_container()
        repo = container.resolve(GraphRepository)
        bus = get_event_bus()

        with self._lock:
            # Save Job entity
            job_entity = Entity(
                uri=job.uri,
                type="job",
                metadata={"workflow_uri": job.workflow_uri, "state": JobState.QUEUED}
            )
            repo.save_entity(job_entity)
            # Relate Job -> instantiates -> Recipe/Workflow
            repo.relate_entities(job.uri, job.workflow_uri, "instantiates")

            # Save Tasks and relate to Job
            for task in tasks:
                task_entity = Entity(
                    uri=task.uri,
                    type="task",
                    metadata={"job_uri": task.job_uri, "state": TaskState.QUEUED, "task_type": task.task_type}
                )
                repo.save_entity(task_entity)
                # Relate Job -> owns -> Task
                repo.relate_entities(job.uri, task.uri, "owns")

        # Set job state to QUEUED and publish event
        job.state = JobState.QUEUED
        bus.publish(Event(
            event_type="job.queued",
            correlation_id=job.uri,
            payload={"job_uri": job.uri, "tasks_count": len(tasks)}
        ))

        # Start execution loop in a background thread
        thread = threading.Thread(target=self._run_job_execution, args=(job, tasks))
        thread.daemon = True
        thread.start()

    def _run_job_execution(self, job: Job, tasks: List[Task]) -> None:
        container = get_container()
        repo = container.resolve(GraphRepository)
        bus = get_event_bus()

        # Update Job state to RUNNING
        job.state = JobState.RUNNING
        repo.save_entity(Entity(
            uri=job.uri,
            type="job",
            metadata={"workflow_uri": job.workflow_uri, "state": JobState.RUNNING}
        ))
        bus.publish(Event(
            event_type="job.started",
            correlation_id=job.uri,
            payload={"job_uri": job.uri}
        ))

        success = True
        try:
            for task in tasks:
                # Update Task state to RUNNING
                task.state = TaskState.RUNNING
                repo.save_entity(Entity(
                    uri=task.uri,
                    type="task",
                    metadata={"job_uri": task.job_uri, "state": TaskState.RUNNING, "task_type": task.task_type}
                ))
                bus.publish(Event(
                    event_type="task.running",
                    correlation_id=job.uri,
                    payload={"task_uri": task.uri, "task_type": task.task_type}
                ))

                # Mock execution latency (Simulates work)
                time.sleep(0.1)

                # Update Task state to COMPLETED
                task.state = TaskState.COMPLETED
                repo.save_entity(Entity(
                    uri=task.uri,
                    type="task",
                    metadata={"job_uri": task.job_uri, "state": TaskState.COMPLETED, "task_type": task.task_type}
                ))
                bus.publish(Event(
                    event_type="task.completed",
                    correlation_id=job.uri,
                    payload={"task_uri": task.uri}
                ))
        except Exception as e:
            success = False
            # Update Job state to FAILED
            job.state = JobState.FAILED
            repo.save_entity(Entity(
                uri=job.uri,
                type="job",
                metadata={"workflow_uri": job.workflow_uri, "state": JobState.FAILED}
            ))
            bus.publish(Event(
                event_type="job.failed",
                correlation_id=job.uri,
                payload={"job_uri": job.uri, "error": str(e)}
            ))

        if success:
            # Update Job state to COMPLETED
            job.state = JobState.COMPLETED
            repo.save_entity(Entity(
                uri=job.uri,
                type="job",
                metadata={"workflow_uri": job.workflow_uri, "state": JobState.COMPLETED}
            ))
            bus.publish(Event(
                event_type="job.completed",
                correlation_id=job.uri,
                payload={"job_uri": job.uri}
            ))
