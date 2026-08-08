from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel, Field

class HostCapabilities(BaseModel):
    supports_timeline: bool = False
    supports_layers: bool = False
    supports_markers: bool = False
    supports_effects: bool = False
    supports_rendering: bool = False
    supports_undo: bool = False

class HostCommand(BaseModel):
    command_id: str
    host: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    undoable: bool = True

class HostAdapter(ABC):
    @abstractmethod
    def get_host_name(self) -> str:
        """Returns the host application name."""
        pass

    @abstractmethod
    def get_capabilities(self) -> HostCapabilities:
        """Returns the capabilities supported by this host application."""
        pass

    @abstractmethod
    def execute_command(self, command: HostCommand) -> bool:
        """Executes a command inside the host application."""
        pass
