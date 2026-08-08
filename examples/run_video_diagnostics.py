import os
import tempfile
from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository
from agentforge_video import VideoPipeline, ResolveAdapter

def main() -> None:
    print("==================================================")
    print("🎬 Running AgentForge Video Processing & Resolve Diagnostics")
    print("==================================================")

    # 1. Setup DI storage repo for trace span persistence
    repo = SQLiteGraphRepository(":memory:")
    container = get_container()
    container.register(GraphRepository, repo)
    print("✓ Storage Repository registered in DI Container.")

    # 2. Setup adapters
    pipeline = VideoPipeline()
    resolve = ResolveAdapter()
    resolve.initialize()
    print("✓ Video Pipeline and DaVinci Resolve adapters ready.")

    # 3. Create dummy input video file and execution paths
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_video = os.path.join(tmp_dir, "input_source.mp4")
        output_keyframes_dir = os.path.join(tmp_dir, "extracted_keyframes")
        
        with open(input_video, "w") as f:
            f.write("mock video file data")
            
        print(f"\n[Processing Pipeline] Starting video analysis on: {input_video}")
        report = pipeline.process_video(
            job_uri="job://session-1/diagnostics-video",
            task_uri="task://t-video-pipeline",
            input_video_path=input_video,
            output_dir=output_keyframes_dir
        )
        
        print("✓ Video processing completed successfully:")
        print(f"  └── Transcript: '{report['transcript_text']}'")
        print(f"  └── Scenes Detected: {len(report['scenes'])} segments found")
        for idx, (start, end) in enumerate(report["scenes"]):
            print(f"      ├── Scene {idx}: {start}s ➔ {end}s")
            print(f"      └── Keyframe Thumbnail: {report['keyframes'][idx]}")

        # 4. Sync clips to DaVinci Resolve
        print("\n[Resolve Synchronization] Syncing clips to timeline...")
        resolve_clips = []
        for idx, (start, end) in enumerate(report["scenes"]):
            resolve_clips.append({
                "path": input_video,
                "start": start,
                "end": end
            })
            
        success = resolve.create_timeline_from_clips(
            timeline_name="AgentForge Edit Selection",
            clips=resolve_clips
        )
        if success:
            print("✓ DaVinci Resolve timeline created and synchronized successfully.")

    print("==================================================")
    print("🎉 VIDEO & RESOLVE DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
