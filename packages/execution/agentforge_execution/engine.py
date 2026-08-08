import time
import threading
from typing import Callable, Any, Dict, Set
from agentforge_core.events import Event, get_event_bus
from agentforge_core.storage import GraphRepository, Entity
from agentforge_core.di import get_container

class TaskTimeoutError(Exception):
    pass

class TaskCancelledError(Exception):
    pass

class ExecutionEngine:
    """
    Execution Engine governing task lifecycles (retries, timeouts, cancellations).
    Emits granular execution status events onto the Event Bus.
    """
    def __init__(self) -> None:
        self._cancelled_tasks: Set[str] = set()
        self._lock = threading.Lock()

    def cancel_task(self, task_uri: str) -> None:
        """
        Marks a task URI as cancelled.
        """
        with self._lock:
            self._cancelled_tasks.add(task_uri)

    def is_cancelled(self, task_uri: str) -> bool:
        with self._lock:
            return task_uri in self._cancelled_tasks

    def run_task(
        self,
        task_uri: str,
        action: Callable[[], Any],
        max_retries: int = 3,
        timeout_seconds: float = 10.0
    ) -> Any:
        """
        Executes the task action wrapping retries, cancellation check, and timeout monitoring.
        """
        bus = get_event_bus()

        retry_count = 0
        while True:
            # 1. Check for cancellation
            if self.is_cancelled(task_uri):
                bus.publish(Event(
                    event_type="task.cancelled",
                    correlation_id=task_uri,
                    payload={"task_uri": task_uri}
                ))
                raise TaskCancelledError(f"Task '{task_uri}' was cancelled by user.")

            # 2. Try executing the task action
            try:
                # Wrap action in a timeout wrapper using thread joins
                result_container: Dict[str, Any] = {}
                exception_container: Dict[str, Any] = {}

                def worker_wrapper():
                    try:
                        result_container["result"] = action()
                    except Exception as err:
                        exception_container["error"] = err

                thread = threading.Thread(target=worker_wrapper)
                thread.daemon = True
                thread.start()
                thread.join(timeout=timeout_seconds)

                if thread.is_alive():
                    raise TaskTimeoutError(f"Task '{task_uri}' timed out after {timeout_seconds}s.")

                if "error" in exception_container:
                    raise exception_container["error"]

                # Success!
                return result_container["result"]

            except Exception as e:
                retry_count += 1
                bus.publish(Event(
                    event_type="task.retry",
                    correlation_id=task_uri,
                    payload={"task_uri": task_uri, "retry": retry_count, "error": str(e)}
                ))
                
                if retry_count >= max_retries:
                    bus.publish(Event(
                        event_type="task.failed",
                        correlation_id=task_uri,
                        payload={"task_uri": task_uri, "error": f"Max retries ({max_retries}) reached: {e}"}
                    ))
                    raise e
                
                # Back-off briefly before retrying
                time.sleep(0.05)
