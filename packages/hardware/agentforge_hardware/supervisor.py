import time
import threading
from typing import Dict, Any, List, Optional
from agentforge_core.di import get_container
from agentforge_core.events import Event, get_event_bus
from agentforge_core.storage import GraphRepository, Entity
from agentforge_hardware.discovery import discover_hardware_capabilities, is_nvml_available
from agentforge_hardware.monitor import get_gpu_metrics

class HardwareSupervisor:
    """
    Background supervisor agent that registers hardware topology in the database
    and monitors GPU/CPU metrics to emit status events onto the Event Bus.
    """
    def __init__(self, check_interval_seconds: float = 1.0) -> None:
        self.interval = check_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._registered_uris: List[str] = []

    def start(self) -> None:
        """
        Starts the supervisor background thread.
        """
        if self._running:
            return
            
        self._running = True
        
        # 1. Discover and Register Hardware Topology in DB
        self.register_hardware_nodes()
        
        # 2. Start monitoring thread
        self._thread = threading.Thread(target=self._monitoring_loop)
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> None:
        """
        Stops the supervisor.
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def register_hardware_nodes(self) -> None:
        """
        Saves hardware components (CPU, RAM, GPU, NVENC/DEC) as addressable nodes in the database.
        These are visualized in 3D as Crystal nodes.
        """
        try:
            container = get_container()
            repo = container.resolve(GraphRepository)
        except Exception:
            # Skip if DB is not registered in DI Container yet (e.g. testing)
            return

        caps = discover_hardware_capabilities()
        
        # 1. Register CPU
        cpu_uri = "hardware://cpu-0"
        repo.save_entity(Entity(
            uri=cpu_uri,
            type="hardware",
            metadata={"name": "Host CPU", "cores": caps.cpu_cores}
        ))
        self._registered_uris.append(cpu_uri)
        
        # 2. Register RAM
        ram_uri = "hardware://ram-0"
        repo.save_entity(Entity(
            uri=ram_uri,
            type="hardware",
            metadata={"name": "Host RAM", "total_gb": round(caps.total_ram_bytes / 1024**3, 1)}
        ))
        self._registered_uris.append(ram_uri)
        
        # 3. Register GPUs
        for gpu in caps.gpus:
            gpu_uri = f"hardware://gpu-{gpu.index}"
            repo.save_entity(Entity(
                uri=gpu_uri,
                type="hardware",
                metadata={"name": gpu.name, "total_vram_gb": round(gpu.total_vram_bytes / 1024**3, 1)}
            ))
            self._registered_uris.append(gpu_uri)
            
            # Relate GPU to CPU
            repo.relate_entities(cpu_uri, gpu_uri, "manages")
            
            # Register codecs if available
            if gpu.has_nvdec:
                dec_uri = f"hardware://gpu-{gpu.index}/nvdec"
                repo.save_entity(Entity(uri=dec_uri, type="hardware", metadata={"name": "NVDEC Decoder"}))
                repo.relate_entities(gpu_uri, dec_uri, "contains")
                self._registered_uris.append(dec_uri)
            if gpu.has_nvenc:
                enc_uri = f"hardware://gpu-{gpu.index}/nvenc"
                repo.save_entity(Entity(uri=enc_uri, type="hardware", metadata={"name": "NVENC Encoder"}))
                repo.relate_entities(gpu_uri, enc_uri, "contains")
                self._registered_uris.append(enc_uri)

    def _monitoring_loop(self) -> None:
        bus = get_event_bus()
        
        # Keep track of low VRAM states to avoid spamming the event bus
        vram_warning_active = False
        gpu_busy_warning_active = False

        while self._running:
            caps = discover_hardware_capabilities()
            for gpu in caps.gpus:
                metrics = get_gpu_metrics(gpu.index)
                if not metrics:
                    continue
                
                # Check VRAM limits (trigger low VRAM warning if free memory < 1.5 GB)
                vram_limit_bytes = 1.5 * 1024 * 1024 * 1024
                if metrics.vram_free_bytes < vram_limit_bytes:
                    if not vram_warning_active:
                        bus.publish(Event(
                            event_type="hardware.vram.low",
                            payload={
                                "gpu_index": gpu.index,
                                "free_vram_mb": round(metrics.vram_free_bytes / 1024**2, 1),
                                "used_vram_mb": round(metrics.vram_used_bytes / 1024**2, 1)
                            }
                        ))
                        vram_warning_active = True
                else:
                    vram_warning_active = False

                # Check core utilization (trigger GPU busy warning if load > 95%)
                if metrics.gpu_utilization_percent > 95.0:
                    if not gpu_busy_warning_active:
                        bus.publish(Event(
                            event_type="hardware.gpu.busy",
                            payload={
                                "gpu_index": gpu.index,
                                "utilization": metrics.gpu_utilization_percent
                            }
                        ))
                        gpu_busy_warning_active = True
                else:
                    gpu_busy_warning_active = False
                    
            time.sleep(self.interval)
