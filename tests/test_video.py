import os
import shutil
import pytest
from agentforge_video import FFmpegWrapper, WhisperWrapper, VideoPipeline, ResolveAdapter

def test_ffmpeg_wrapper_fallback(tmp_path):
    wrapper = FFmpegWrapper()
    input_file = tmp_path / "test_input.mp4"
    output_file = tmp_path / "test_output.mp4"
    
    # Create mock input file
    input_file.write_text("dummy video data")
    
    # Execute transcoding
    artifact = wrapper.transcode_video(
        job_uri="job://session-1/transcode",
        task_uri="task://t1",
        input_path=str(input_file),
        output_path=str(output_file)
    )
    
    assert artifact.type == "video"
    assert artifact.file_path == str(output_file)
    assert os.path.exists(output_file)

def test_whisper_transcription():
    wrapper = WhisperWrapper()
    # Non-existent input path triggers mock segment fallbacks
    artifact = wrapper.transcribe_audio(
        job_uri="job://session-1/transcribe",
        task_uri="task://t2",
        input_path="/nonexistent/audio.wav"
    )
    assert artifact.type == "transcript"
    assert len(artifact.segments) > 0
    assert "CUDA" in artifact.segments[1].text

def test_video_pipeline(tmp_path):
    pipeline = VideoPipeline()
    input_file = tmp_path / "video.mp4"
    input_file.write_text("mock mp4 metadata")
    
    report = pipeline.process_video(
        job_uri="job://session-1/pipeline",
        task_uri="task://t3",
        input_video_path=str(input_file),
        output_dir=str(tmp_path / "keyframes")
    )
    
    assert "scenes" in report
    assert len(report["keyframes"]) > 0
    assert "transcript_uri" in report

def test_resolve_adapter():
    import time
    adapter = ResolveAdapter()
    assert adapter.initialize() is True
    clips = [{"path": "/path/clip.mp4", "start": 0.0, "end": 5.0}]
    timeline_name = f"Demo Timeline {int(time.time())}"
    assert adapter.create_timeline_from_clips(timeline_name, clips) is True
