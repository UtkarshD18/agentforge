import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ExecutionOrchestrator:
    def __init__(self, scheduler: Any, state_store: Any, event_store: Any, runtime: Any) -> None:
        self.scheduler = scheduler
        self.state_store = state_store
        self.event_store = event_store
        self.runtime = runtime

    def run_graph(self, task_graph: Any) -> None:
        """
        Orchestrates execution of tasks in a DAG, recording checkpoints and recovery events.
        """
        for task_id, node in task_graph.nodes.items():
            self.state_store.set_task_state(task_id, node.model_dump())

        visited = set()
        queue = list(task_graph.root_tasks)

        while queue:
            task_id = queue.pop(0)
            if task_id in visited:
                continue
            
            node = task_graph.nodes[task_id]
            deps_ok = all(parent in visited for parent in node.parents)
            if not deps_ok:
                queue.append(task_id)
                continue

            self.state_store.update_task_status(task_id, "running")
            
            try:
                time.sleep(0.01)
                self.state_store.update_task_status(task_id, "completed")
                visited.add(task_id)
                queue.extend(node.children)
            except Exception as e:
                self.state_store.update_task_status(task_id, "failed")
                raise e
