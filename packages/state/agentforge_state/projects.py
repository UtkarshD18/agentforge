import threading
from typing import Dict, Any, Optional

class ProjectStateStore:
    def __init__(self) -> None:
        self._projects: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def set_project(self, project_id: str, details: Dict[str, Any]) -> None:
        with self._lock:
            self._projects[project_id] = details

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._projects.get(project_id)

    def update_project_graphs(self, project_id: str, graphs: Dict[str, str]) -> None:
        with self._lock:
            if project_id in self._projects:
                self._projects[project_id]["graphs"] = graphs
