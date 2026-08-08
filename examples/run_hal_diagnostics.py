from agentforge_hardware.manager import HardwareManager
from agentforge_hardware.interfaces import AcceleratorFrame

def main() -> None:
    print("==================================================")
    print("🚀 Running AgentForge HAL Auto-Discovery Diagnostics")
    print("==================================================")

    # 1. Detect and register active backend
    backend = HardwareManager.auto_detect_and_register()
    backend_name = backend.__class__.__name__
    print(f"✓ Detected Active Compute Backend: {backend_name}")

    # 2. Query capabilities
    caps = backend.get_capabilities()
    print(f"✓ CPU Cores: {caps.cpu_cores}")
    print(f"✓ Total RAM: {round(caps.total_ram_bytes / 1024**3, 2)} GB")
    
    print(f"✓ Detected GPUs: {len(caps.gpus)}")
    for gpu in caps.gpus:
        print(f"  - [{gpu.index}] {gpu.name} (VRAM: {round(gpu.total_vram_bytes / 1024**3, 1)} GB)")

    # 3. Test Memory Pool Allocation
    pool = backend.get_memory_pool(device_index=0)
    size_bytes = 1024 * 1024 * 4  # 4 MB frame
    ptr = pool.acquire_buffer(size_bytes)
    print(f"✓ Memory Pool Allocation: Acquired 4MB buffer at pointer {hex(ptr)}")

    # 4. Wrap as an AcceleratorFrame
    frame = AcceleratorFrame(
        memory_pointer=ptr,
        width=1920,
        height=1080,
        format="nv12",
        timestamp_seconds=0.0,
        backend_type="cuda" if caps.gpus else "cpu"
    )
    print(f"✓ Instantiated AcceleratorFrame metadata: {frame.width}x{frame.height} | Backend: {frame.backend_type}")

    # 5. Test Stream Creation
    streams = backend.get_stream_manager(device_index=0)
    stream = streams.create_stream("render_pipeline")
    print(f"✓ Stream Manager: Created execution stream: {stream}")

    # 6. Release Memory
    pool.release_buffer(ptr)
    print("✓ Memory Pool Release: Released buffer pointer.")

    print("==================================================")
    print("🎉 HAL DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
