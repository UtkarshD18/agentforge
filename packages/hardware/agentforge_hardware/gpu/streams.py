import threading
from typing import List

class CUDAStreamManager:
    """
    Mock wrapper representing multiple parallel CUDA Execution Streams.
    Allows Scheduler to overlap task run queues on the same hardware GPU context.
    """
    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self._active_streams: List[str] = []
        self._lock = threading.Lock()

    def create_stream(self, name: str) -> str:
        """
        Allocates a new CUDA execution stream queue.
        """
        with self._lock:
            if name not in self._active_streams:
                self._active_streams.append(name)
            return f"cuda_stream_{self.device_index}_{name}"

    def get_streams(self) -> List[str]:
        """
        Returns active streams list.
        """
        with self._lock:
            return list(self._active_streams)
