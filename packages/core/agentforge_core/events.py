import time
import uuid
import asyncio
import inspect
import threading
from typing import Any, Callable, Dict, List, Coroutine, Union
from pydantic import BaseModel, Field

class Event(BaseModel):
    """
    Versioned Event schema mapping all system state changes.
    """
    version: str = "1.0"
    event_type: str
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = Field(default_factory=dict)

# Type for callbacks: supports both normal sync callables and async coroutines
EventCallback = Callable[[Event], Union[None, Coroutine[Any, Any, None]]]

class EventBus:
    """
    Thread-safe Event Bus for publishing and subscribing to AgentForge system events.
    """
    def __init__(self) -> None:
        self._subscribers: List[EventCallback] = []
        self._lock = threading.Lock()

    def subscribe(self, callback: EventCallback) -> None:
        """
        Registers a callback subscription.
        """
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: EventCallback) -> None:
        """
        Removes a callback subscription.
        """
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def publish(self, event: Event) -> None:
        """
        Broadcasts the event to all subscribers.
        Synchronous callbacks execute immediately. Asynchronous callbacks are scheduled
        on the running event loop, or executed in a temporary loop if none exists.
        """
        with self._lock:
            subscribers = list(self._subscribers)

        for callback in subscribers:
            try:
                if inspect.iscoroutinefunction(callback):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(callback(event))  # type: ignore
                    except RuntimeError:
                        # Run synchronously in a temporary loop if no loop is running
                        asyncio.run(callback(event))  # type: ignore
                else:
                    callback(event)
            except Exception as e:
                import sys
                print(f"[EventBus Error] Callback {callback.__name__ if hasattr(callback, '__name__') else callback} failed: {e}", file=sys.stderr)

# Global singleton Event Bus
_global_bus = EventBus()

def get_event_bus() -> EventBus:
    """
    Access the global singleton Event Bus instance.
    """
    return _global_bus
