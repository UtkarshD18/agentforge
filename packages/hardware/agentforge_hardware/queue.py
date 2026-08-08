import time
import queue
import threading
from typing import Callable, Any, Dict, Optional
from agentforge_hardware.broker import get_device_broker

class ComputeQueue:
    """
    Queue manager bound to a specific hardware device.
    Verifies VRAM availability with the DeviceBroker before launching tasks.
    """
    def __init__(self, device_index: int, device_name: str) -> None:
        self.device_index = device_index
        self.device_name = device_name
        self._queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """
        Starts the worker processing loop.
        """
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._process_queue)
            self._thread.daemon = True
            self._thread.start()

    def stop(self) -> None:
        """
        Stops the worker thread.
        """
        with self._lock:
            self._running = False
            
        if self._thread:
            # Enqueue a sentinel to wake up the queue get blocker
            self._queue.put(None)
            self._thread.join(timeout=1.0)

    def submit_task(self, task_name: str, vram_required_bytes: int, action: Callable[[], Any]) -> None:
        """
        Enqueues a task requesting specific VRAM memory.
        """
        self._queue.put({
            "name": task_name,
            "vram_bytes": vram_required_bytes,
            "action": action
        })

    def _process_queue(self) -> None:
        broker = get_device_broker()

        while True:
            with self._lock:
                if not self._running:
                    break

            try:
                # Block for 0.5s waiting for a task
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is None:
                # Sentinel shutdown request
                break

            task_name = item["name"]
            vram_req = item["vram_bytes"]
            action = item["action"]

            # Loop/Poll memory reservation until VRAM headroom is granted by the broker
            # This implements the Resource Reservation backlog checks.
            while True:
                with self._lock:
                    if not self._running:
                        break
                        
                if broker.reserve_vram(self.device_index, vram_req):
                    break
                # Back-off briefly before retrying allocation
                time.sleep(0.1)

            with self._lock:
                if not self._running:
                    broker.release_vram(self.device_index, vram_req)
                    break

            # Execute action
            try:
                action()
            except Exception as e:
                import sys
                print(f"[ComputeQueue Error] Task '{task_name}' failed on {self.device_name}: {e}", file=sys.stderr)
            finally:
                broker.release_vram(self.device_index, vram_req)
                self._queue.task_done()
