import pytest
from pydantic import ValidationError
from agentforge_core.workflow import (
    VideoArtifact,
    AudioArtifact,
    SubtitleArtifact,
    TextArtifact,
    TranscriptArtifact,
    TranscriptSegment
)

def test_video_artifact_validation():
    # Valid instantiation
    vid = VideoArtifact(
        uri="artifact://job1/vid1",
        job_uri="job://job1",
        task_uri="task://job1/t1",
        file_path="/path/to/clip.mp4",
        duration_seconds=12.5,
        width=1920,
        height=1080
    )
    assert vid.type == "video"
    assert vid.width == 1920
    assert vid.duration_seconds == 12.5

    # Missing required field width/height
    with pytest.raises(ValidationError):
        VideoArtifact(
            uri="artifact://job1/vid2",
            job_uri="job://job1",
            task_uri="task://job1/t1",
            file_path="/path/to/clip.mp4",
            duration_seconds=12.5
        )

def test_audio_artifact_validation():
    aud = AudioArtifact(
        uri="artifact://job1/aud1",
        job_uri="job://job1",
        task_uri="task://job1/t1",
        file_path="/path/to/audio.wav",
        duration_seconds=60.0
    )
    assert aud.type == "audio"
    assert aud.sample_rate == 44100

def test_subtitle_artifact_validation():
    sub = SubtitleArtifact(
        uri="artifact://job1/sub1",
        job_uri="job://job1",
        task_uri="task://job1/t1",
        file_path="/path/to/subs.srt",
        language="hi"
    )
    assert sub.type == "subtitle"
    assert sub.language == "hi"

def test_text_artifact_validation():
    txt = TextArtifact(
        uri="artifact://job1/txt1",
        job_uri="job://job1",
        task_uri="task://job1/t1",
        text_content="Generated video screenplay details"
    )
    assert txt.type == "text"
    assert txt.text_content == "Generated video screenplay details"

def test_transcript_artifact_validation():
    trans = TranscriptArtifact(
        uri="artifact://job1/trans1",
        job_uri="job://job1",
        task_uri="task://job1/t1",
        segments=[
            TranscriptSegment(start_seconds=0.0, end_seconds=2.0, text="Hello world"),
            TranscriptSegment(start_seconds=2.0, end_seconds=5.0, text="Welcome to AgentForge OS")
        ]
    )
    assert trans.type == "transcript"
    assert len(trans.segments) == 2
    assert trans.segments[1].text == "Welcome to AgentForge OS"
