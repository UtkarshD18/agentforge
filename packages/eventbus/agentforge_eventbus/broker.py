import asyncio
import inspect
import threading
from typing import Any, Callable, List, Coroutine, Union
from .events import Event

EventCallback = Callable[[Event], Union[None, Coroutine[Any, Any, None]]]

class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[EventCallback] = []
        self._lock = threading.Lock()

    def subscribe(self, callback: EventCallback) -> None:
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: EventCallback) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def publish(self, event: Event) -> None:
        with self._lock:
            subscribers = list(self._subscribers)

        for callback in subscribers:
            try:
                if inspect.iscoroutinefunction(callback):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(callback(event))  # type: ignore
                    except RuntimeError:
                        asyncio.run(callback(event))  # type: ignore
                else:
                    callback(event)
            except Exception as e:
                import sys
                print(f"[EventBus Error] Callback failed: {e}", file=sys.stderr)

_global_bus = EventBus()

def get_event_bus() -> EventBus:
    return _global_bus
