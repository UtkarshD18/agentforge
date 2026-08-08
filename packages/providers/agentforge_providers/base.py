from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field

class ProviderHealth(BaseModel):
    latency_ms: float = 0.0
    availability: float = 1.0
    rate_limit_percentage: float = 0.0
    queue_depth: int = 0
    last_failure_timestamp: Optional[float] = None
    estimated_cost_per_token: float = 0.0

class CapabilityProvider(ABC):
    @abstractmethod
    def execute(self, unit: Any, context: Any) -> Any:
        """
        Executes a task unit given the execution context.
        """
        pass

    @abstractmethod
    def get_health(self) -> ProviderHealth:
        """
        Returns live health metrics.
        """
        pass
