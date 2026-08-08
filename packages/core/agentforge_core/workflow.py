from typing import Any, Dict
from pydantic import BaseModel, Field

class JobState:
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_RESOURCE = "waiting_resource"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskState:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(BaseModel):
    """
    Job entity representing an active execution run of a workflow.
    """
    uri: str
    workflow_uri: str
    state: str = JobState.DRAFT
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Task(BaseModel):
    """
    Task entity representing an individual step in a Job run.
    """
    uri: str
    job_uri: str
    state: str = TaskState.QUEUED
    task_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Artifact(BaseModel):
    """
    Base Artifact entity representing immutable data consumed/produced by Tasks.
    """
    uri: str
    job_uri: str
    task_uri: str
    type: str = "generic"
    data: Dict[str, Any] = Field(default_factory=dict)

class VideoArtifact(Artifact):
    """
    Typed artifact representing a video clip.
    """
    type: str = "video"
    file_path: str
    duration_seconds: float
    width: int
    height: int
    codec: str = "h264"

class AudioArtifact(Artifact):
    """
    Typed artifact representing an audio track.
    """
    type: str = "audio"
    file_path: str
    duration_seconds: float
    sample_rate: int = 44100
    channels: int = 2

class SubtitleArtifact(Artifact):
    """
    Typed artifact representing subtitles.
    """
    type: str = "subtitle"
    file_path: str
    language: str = "en"
    format: str = "srt"

class TextArtifact(Artifact):
    """
    Typed artifact representing raw generated/processed text.
    """
    type: str = "text"
    text_content: str
    token_count: int = 0

class TranscriptSegment(BaseModel):
    start_seconds: float
    end_seconds: float
    text: str

class TranscriptArtifact(Artifact):
    """
    Typed artifact representing audio transcription segments.
    """
    type: str = "transcript"
    segments: list[TranscriptSegment] = Field(default_factory=list)

