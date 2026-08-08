from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class GPUFrame(BaseModel):
    """
    Metadata wrapper representing a video frame allocated directly on GPU VRAM.
    Allows zero-copy data passing between local filter and render plugins.
    """
    cuda_pointer: int                 # Memory address pointer on VRAM
    width: int
    height: int
    format: str = "nv12"              # Codec format (e.g. nv12, yuv420p)
    timestamp_seconds: float
    device_index: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CUDAMemoryPool:
    """
    Mock/Stub memory manager for a pre-allocated CUDA memory pool.
    Prevents costly runtime allocate/free CUDA calls.
    """
    def __init__(self, device_index: int = 0, pool_size_mb: int = 512) -> None:
        self.device_index = device_index
        self.pool_size_bytes = pool_size_mb * 1024 * 1024
        self._allocated_pointers: Dict[int, int] = {}  # ptr -> size
        self._next_pointer = 0x7f0000000000            # Mock base memory address

    def acquire_buffer(self, size_bytes: int) -> int:
        """
        Acquires a VRAM buffer pointer from the pool.
        """
        ptr = self._next_pointer
        self._allocated_pointers[ptr] = size_bytes
        self._next_pointer += size_bytes
        return ptr

    def release_buffer(self, ptr: int) -> None:
        """
        Releases a buffer back into the pool.
        """
        if ptr in self._allocated_pointers:
            del self._allocated_pointers[ptr]
