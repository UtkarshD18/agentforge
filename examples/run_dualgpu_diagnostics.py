import os
from agentforge_hardware.backends.nvidia.backend import NvidiaBackend
from agentforge_hardware.backends.intel.backend import IntelBackend
from agentforge_hardware.backends.amd.backend import AMDBackend

def main() -> None:
    print("==================================================")
    print("🚀 Running AgentForge Dual-GPU Discovery Diagnostics")
    print("==================================================")

    # 1. Direct DRM cataloging
    drm_path = "/sys/class/drm"
    print(f"📁 DRM Card Devices Path: {drm_path}")
    if os.path.exists(drm_path):
        cards = [c for c in os.listdir(drm_path) if c.startswith("card")]
        print(f"  - Found DRM card nodes: {cards}")
        for card in cards:
            vendor_file = os.path.join(drm_path, card, "device", "vendor")
            if os.path.exists(vendor_file):
                with open(vendor_file, "r") as f:
                    vendor_id = f.read().strip()
                vendor_name = "Unknown"
                if "0x8086" in vendor_id:
                    vendor_name = "Intel Corporation"
                elif "0x10de" in vendor_id:
                    vendor_name = "NVIDIA Corporation"
                elif "0x1002" in vendor_id:
                    vendor_name = "Advanced Micro Devices (AMD)"
                print(f"  - Card: {card} | Vendor ID: {vendor_id} ({vendor_name})")
    else:
        print("  - DRM system directories not found (e.g. non-Linux system or headless container)")

    # 2. Test NVIDIA Backend discovery
    print("\n[Backend Test: NVIDIA]")
    nv_backend = NvidiaBackend()
    if nv_backend.initialize():
        caps = nv_backend.get_capabilities()
        print(f"  - Initialized successfully: Yes")
        print(f"  - Discovered GPUs: {len(caps.gpus)}")
        for g in caps.gpus:
            print(f"    * Index {g.index}: {g.name} | VRAM: {round(g.total_vram_bytes / 1024**3, 2)} GB")
    else:
        print("  - Initialized successfully: No (Driver or hardware not active)")

    # 3. Test Intel Backend discovery
    print("\n[Backend Test: Intel Integrated]")
    intel_backend = IntelBackend()
    if intel_backend.initialize():
        caps = intel_backend.get_capabilities()
        print(f"  - Initialized successfully: Yes")
        print(f"  - Discovered Intel GPUs: {len(caps.gpus)}")
        for g in caps.gpus:
            print(f"    * Index {g.index}: {g.name} | Shared VRAM Budget: {round(g.total_vram_bytes / 1024**3, 2)} GB")
    else:
        print("  - Initialized successfully: No (Intel DRM cards not active in sysfs)")

    # 4. Test AMD Backend discovery
    print("\n[Backend Test: AMD Radeon]")
    amd_backend = AMDBackend()
    if amd_backend.initialize():
        caps = amd_backend.get_capabilities()
        print(f"  - Initialized successfully: Yes")
        print(f"  - Discovered AMD GPUs: {len(caps.gpus)}")
        for g in caps.gpus:
            print(f"    * Index {g.index}: {g.name} | VRAM: {round(g.total_vram_bytes / 1024**3, 2)} GB")
    else:
        print("  - Initialized successfully: No (AMD DRM cards not active in sysfs)")

    print("\n==================================================")
    print("🎉 DUAL-GPU DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
