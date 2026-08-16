import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ResourceAcquisitionError(Exception):
    """
    Error raised when ResourceManager safety ceilings or limits prevent model loading.
    """
    pass

class Reservation(BaseModel):
    reservation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str
    allocated_vram_bytes: int
    active: bool = True

class ReservationContext:
    def __init__(self, planner: "MemoryPlanner", model_name: str, required_vram: int) -> None:
        self.planner = planner
        self.model_name = model_name
        self.required_vram = required_vram
        self.reservation: Optional[Reservation] = None

    def __enter__(self) -> Reservation:
        res = self.planner.acquire_reservation(self.model_name, self.required_vram)
        if not res:
            raise ResourceAcquisitionError(
                f"Cannot fit model '{self.model_name}' requiring {self.required_vram} VRAM bytes. "
                "Total allocated exceeds safety ceiling."
            )
        self.reservation = res
        return res

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.reservation:
            self.planner.release_reservation(self.reservation)

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

    def acquire(self, model_name: str, required_vram: int) -> ReservationContext:
        """
        Returns a context manager wrapper to load/unload models safely.
        """
        return ReservationContext(self, model_name, required_vram)
