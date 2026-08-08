import threading
from typing import Dict, Any, Optional

class TaskStateStore:
    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def set_task_state(self, task_id: str, state: Dict[str, Any]) -> None:
        with self._lock:
            self._tasks[task_id] = state

    def update_task_status(self, task_id: str, status: str) -> None:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = status

    def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._tasks)
