import json
import os
from typing import List
from .events import Event

class EventStore:
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        dirpath = os.path.dirname(filepath)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

    def append(self, event: Event) -> None:
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def read_all(self) -> List[dict]:
        if not os.path.exists(self.filepath):
            return []
        events = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events
