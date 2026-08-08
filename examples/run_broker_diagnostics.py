import time
from agentforge_hardware.manager import HardwareManager
from agentforge_hardware.broker import get_device_broker
from agentforge_hardware.queue import ComputeQueue

def main() -> None:
    print("==================================================")
    print("🚀 Running AgentForge DeviceBroker & Queue Diagnostics")
    print("==================================================")

    # 1. Initialize active backend
    backend = HardwareManager.auto_detect_and_register()
    print(f"✓ Active Backend Registered: {backend.__class__.__name__}")

    broker = get_device_broker()
    
    # 2. Setup parallel queues
    queue0 = ComputeQueue(device_index=0, device_name="Accelerator-0")
    queue1 = ComputeQueue(device_index=1, device_name="Accelerator-1")
    
    queue0.start()
    queue1.start()
    print("✓ Spawned parallel ComputeQueues for Accelerator-0 and Accelerator-1.")

    task_log = []
    
    def task_action_a():
        task_log.append("Task A Running")
        # Query reservations from the broker while running
        res = broker.get_reservations(device_index=0)
        print(f"  [Task A Action] Active reservations: {res}")
        time.sleep(0.2)
        task_log.append("Task A Done")

    def task_action_b():
        task_log.append("Task B Running")
        res = broker.get_reservations(device_index=1)
        print(f"  [Task B Action] Active reservations: {res}")
        time.sleep(0.2)
        task_log.append("Task B Done")

    # 3. Submit safe task requests (e.g. 50MB VRAM)
    print("\n[Submit Phase] Enqueuing tasks with broker reservations...")
    queue0.submit_task(
        task_name="whisper_transcription",
        vram_required_bytes=50 * 1024**2,
        action=task_action_a
    )
    
    queue1.submit_task(
        task_name="ffmpeg_transcode",
        vram_required_bytes=100 * 1024**2,
        action=task_action_b
    )

    # 4. Wait for processing to complete
    time.sleep(0.6)
    
    queue0.stop()
    queue1.stop()

    print("\n[Execution Log]")
    for entry in task_log:
        print(f"  - {entry}")

    print("==================================================")
    print("🎉 BROKER & QUEUE DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
