import threading
from typing import Dict, Any, Optional

class WorkerStateStore:
    def __init__(self) -> None:
        self._workers: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register_worker(self, worker_id: str, profile: Dict[str, Any]) -> None:
        with self._lock:
            self._workers[worker_id] = {
                "profile": profile,
                "metrics": {},
                "running_tasks": []
            }

    def update_metrics(self, worker_id: str, metrics: Dict[str, Any]) -> None:
        with self._lock:
            if worker_id in self._workers:
                self._workers[worker_id]["metrics"] = metrics

    def update_running_tasks(self, worker_id: str, running_tasks: list) -> None:
        with self._lock:
            if worker_id in self._workers:
                self._workers[worker_id]["running_tasks"] = running_tasks

    def get_worker_state(self, worker_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._workers.get(worker_id)

    def get_all_workers(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._workers)
