import os
import sys
from typing import List, Optional
from pydantic import BaseModel

# Try importing pynvml from nvidia-ml-py
try:
    import pynvml
    _NVML_AVAILABLE = True
except ImportError:
    _NVML_AVAILABLE = False

class GPUCapabilities(BaseModel):
    """
    Exportable specs for a single local GPU device.
    """
    index: int
    name: str
    total_vram_bytes: int
    cuda_version: Optional[str] = None
    driver_version: Optional[str] = None
    has_nvdec: bool = False
    has_nvenc: bool = False

class HardwareCapabilities(BaseModel):
    """
    System-wide hardware profile exported to the Scheduler.
    """
    cpu_cores: int
    total_ram_bytes: int
    gpus: List[GPUCapabilities] = []

def is_nvml_available() -> bool:
    """
    Check if NVIDIA management library is importable and initialized.
    """
    if not _NVML_AVAILABLE:
        return False
    try:
        pynvml.nvmlInit()
        return True
    except Exception:
        return False

def discover_hardware_capabilities() -> HardwareCapabilities:
    """
    Queries OS and NVML bindings to discover CPU, RAM, and GPU capabilities.
    """
    # 1. Discover CPU Cores
    cpu_cores = os.cpu_count() or 1
    
    # 2. Discover Total RAM (using zero-dependency POSIX page size query)
    total_ram = 0
    try:
        page_size = os.sysconf('SC_PAGE_SIZE')
        phys_pages = os.sysconf('SC_PHYS_PAGES')
        total_ram = page_size * phys_pages
    except Exception:
        # Fallback if POSIX sysconf is not supported (e.g. non-Linux systems)
        total_ram = 8 * 1024 * 1024 * 1024  # Default mock 8GB
        
    gpus: List[GPUCapabilities] = []
    
    # 3. Discover GPUs via NVML
    if is_nvml_available():
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            driver_ver = pynvml.nvmlSystemGetDriverVersion().decode("utf-8")
            
            # CUDA version is encoded as integer (e.g., 12010 represents 12.1)
            try:
                cuda_int = pynvml.nvmlSystemGetCudaDriverVersion()
                cuda_ver = f"{cuda_int // 1000}.{(cuda_int % 1000) // 10}"
            except Exception:
                cuda_ver = "Unknown"

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                gpu_name = pynvml.nvmlDeviceGetName(handle)
                # Handle bytes vs string encoding across different NVML bindings
                if isinstance(gpu_name, bytes):
                    gpu_name = gpu_name.decode("utf-8")
                    
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_vram = mem_info.total
                
                # Check for standard hardware codec capability
                # We assume standard modern NVIDIA GPUs have NVDEC/NVENC capability
                has_nvdec = True
                has_nvenc = True
                
                gpus.append(GPUCapabilities(
                    index=i,
                    name=gpu_name,
                    total_vram_bytes=total_vram,
                    cuda_version=cuda_ver,
                    driver_version=driver_ver,
                    has_nvdec=has_nvdec,
                    has_nvenc=has_nvenc
                ))
        except Exception as e:
            # Gracing fallback on driver failure or VM environments
            import sys
            print(f"[HAL Warning] Failed to fetch detailed NVML specs: {e}", file=sys.stderr)
        finally:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
                
    return HardwareCapabilities(
        cpu_cores=cpu_cores,
        total_ram_bytes=total_ram,
        gpus=gpus
    )
