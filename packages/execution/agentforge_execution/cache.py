import hashlib
import json
import threading
from typing import Dict, Any, Optional
from agentforge_core.workflow import Artifact

class ArtifactCache:
    """
    Thread-safe Cache keying off SHA256 checksums of input parameters and versions.
    Allows bypassing heavy video rendering and AI inference calls on identical runs.
    """
    def __init__(self) -> None:
        self._cache: Dict[str, Artifact] = {}
        self._lock = threading.Lock()

    @staticmethod
    def generate_checksum(inputs: Dict[str, Any]) -> str:
        """
        Creates a stable SHA-256 checksum hash key for a dictionary of inputs.
        """
        # Sort keys to ensure stable hashing output
        serialized = json.dumps(inputs, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get_cached_artifact(self, input_checksum: str, version: str) -> Optional[Artifact]:
        """
        Retrieves a cached Artifact if checksum and version match.
        """
        key = f"{input_checksum}:{version}"
        with self._lock:
            return self._cache.get(key)

    def set_cached_artifact(self, input_checksum: str, version: str, artifact: Artifact) -> None:
        """
        Stores an output Artifact under the input checksum and version key.
        """
        key = f"{input_checksum}:{version}"
        with self._lock:
            self._cache[key] = artifact

    def clear(self) -> None:
        """
        Clears the cache (useful for testing).
        """
        with self._lock:
            self._cache.clear()
