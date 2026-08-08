from typing import Dict, Any, Optional
from pydantic import BaseModel
from agentforge_hardware.discovery import is_nvml_available

# Try importing pynvml
try:
    import pynvml
except ImportError:
    pass

class GPUMetrics(BaseModel):
    """
    Real-time telemetry metrics for a local GPU.
    """
    index: int
    gpu_utilization_percent: float
    memory_utilization_percent: float
    vram_used_bytes: int
    vram_free_bytes: int
    temperature_celsius: float
    power_draw_watts: float

def get_gpu_metrics(device_index: int) -> Optional[GPUMetrics]:
    """
    Queries NVML to fetch real-time utilization, memory, temperature, and power for a GPU.
    Returns None if NVML is not available.
    """
    if not is_nvml_available():
        return None
        
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
        
        # 1. Query Utilization (GPU core and memory controller)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_util = float(util.gpu)
        mem_util = float(util.memory)
        
        # 2. Query VRAM usage
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_used = mem_info.used
        vram_free = mem_info.free
        
        # 3. Query Temperature
        temp = float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
        
        # 4. Query Power Draw (converted milliwatts to watts)
        try:
            power = float(pynvml.nvmlDeviceGetPowerUsage(handle)) / 1000.0
        except Exception:
            power = 0.0
            
        return GPUMetrics(
            index=device_index,
            gpu_utilization_percent=gpu_util,
            memory_utilization_percent=mem_util,
            vram_used_bytes=vram_used,
            vram_free_bytes=vram_free,
            temperature_celsius=temp,
            power_draw_watts=power
        )
    except Exception:
        return None
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
