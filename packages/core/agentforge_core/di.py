import threading
from typing import Any, Dict, Type, TypeVar

T = TypeVar("T")

class Container:
    """
    Thread-safe Dependency Injection Container for AgentForge OS services.
    """
    def __init__(self) -> None:
        self._services: Dict[Type[Any], Any] = {}
        self._lock = threading.Lock()

    def register(self, interface: Type[T], instance: T) -> None:
        """
        Registers a concrete service instance under its interface type.
        """
        with self._lock:
            self._services[interface] = instance

    def resolve(self, interface: Type[T]) -> T:
        """
        Retrieves the registered service instance for the requested interface type.
        Raises a ValueError if the service is not found in the container.
        """
        with self._lock:
            if interface not in self._services:
                raise ValueError(f"Dependency '{interface.__name__}' has not been registered in the DI container.")
            return self._services[interface]

    def clear(self) -> None:
        """
        Removes all registered services (useful for clearing test states).
        """
        with self._lock:
            self._services.clear()

# Global singleton DI Container
_global_container = Container()

def get_container() -> Container:
    """
    Get the global singleton container instance.
    """
    return _global_container
