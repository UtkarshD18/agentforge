import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class Reservation(BaseModel):
    reservation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str
    allocated_vram_bytes: int
    active: bool = True

class MemoryPlanner:
    def __init__(self, resource_manager: Any, model_manager: Any) -> None:
        self.resource_manager = resource_manager
        self.model_manager = model_manager
        self.active_reservations: Dict[str, Reservation] = {}

    def acquire_reservation(self, model_name: str, required_vram: int) -> Optional[Reservation]:
        if self.model_manager.load_model(model_name, required_vram):
            res = Reservation(model_name=model_name, allocated_vram_bytes=required_vram)
            self.active_reservations[res.reservation_id] = res
            return res
        return None

    def release_reservation(self, reservation: Reservation) -> None:
        if reservation.reservation_id in self.active_reservations:
            reservation.active = False
            self.model_manager.unload_model(reservation.model_name)
            del self.active_reservations[reservation.reservation_id]
