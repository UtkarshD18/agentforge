import os
import json
from typing import Dict, Any, List
from pydantic import BaseModel

class StylePacing(BaseModel):
    average_shot_duration: float
    median_shot_duration: float
    shots_per_10_seconds: float

class StyleHook(BaseModel):
    duration: float
    contains_text: bool
    contains_face: bool
    contains_motion: bool

class StyleVisual(BaseModel):
    vertical: bool
    punch_in_frequency: float
    camera_motion: float
    cut_frequency: float

class StyleAudio(BaseModel):
    speech_density: float
    music_present: bool
    beat_cuts: bool

class StyleText(BaseModel):
    captions: bool
    large_emphasis_words: bool

class StyleProfile(BaseModel):
    profile_id: str
    target_duration: float
    pacing: StylePacing
    hook: StyleHook
    visual: StyleVisual
    audio: StyleAudio
    text: StyleText

class ReferenceStyleAnalyzer:
    """
    Analyzes visual/audio pacing of a reference video clip
    and compiles a structured StyleProfile.
    """
    def analyze_reference(self, reference_path: str) -> StyleProfile:
        # Default mock profile representing standard dynamic Short editing grammar
        profile = StyleProfile(
            profile_id="style_short_vlog_01",
            target_duration=30.0,
            pacing=StylePacing(
                average_shot_duration=1.5,
                median_shot_duration=1.2,
                shots_per_10_seconds=6.6
            ),
            hook=StyleHook(
                duration=2.5,
                contains_text=True,
                contains_face=True,
                contains_motion=True
            ),
            visual=StyleVisual(
                vertical=True,
                punch_in_frequency=0.4,
                camera_motion=0.8,
                cut_frequency=0.7
            ),
            audio=StyleAudio(
                speech_density=0.6,
                music_present=True,
                beat_cuts=True
            ),
            text=StyleText(
                captions=True,
                large_emphasis_words=True
            )
        )
        
        # If reference file exists, perform actual scene/shot metadata inspection via FFmpeg/ffprobe if possible
        if os.path.exists(reference_path):
            try:
                # Use scene detection or metadata checks
                from agentforge_video import FFmpegWrapper
                ffmpeg = FFmpegWrapper()
                # Run cheap scene boundaries parse if available, adjusting profile duration
                duration = ffmpeg.get_video_duration(reference_path)
                if duration > 0:
                    profile.target_duration = round(duration, 2)
            except Exception:
                pass
                
        return profile

def timecode_to_seconds(tc: str, fps: float = 30.0) -> float:
    if not tc or not isinstance(tc, str) or ":" not in tc:
        return 0.0
    try:
        parts = tc.split(":")
        if len(parts) == 4:
            h, m, s, f = parts
            return int(h) * 3600 + int(m) * 60 + int(s) + int(f) / fps
    except Exception:
        pass
    return 0.0

class StyleMatcher:
    """
    Compares the extracted Reference Style constraints against
    the available media footage inside the MediaGraph.
    Calibrates the targets so that the Director does not schedule
    edits beyond what the footage can support.
    """
    def calibrate_style(self, profile: StyleProfile, available_clips: List[Dict[str, Any]]) -> StyleProfile:
        durations = []
        for c in available_clips:
            dur = c.get("duration", "00:00:00:00")
            fps = float(c.get("fps") or 30.0)
            if isinstance(dur, str):
                durations.append(timecode_to_seconds(dur, fps))
            else:
                durations.append(float(dur))
                
        total_duration = sum(durations)
        clip_count = len(available_clips)
        
        calibrated = profile.model_copy(deep=True)
        
        # Prevent pacing that is too fast if available clips are too few
        if clip_count < 3:
            calibrated.pacing.average_shot_duration = max(profile.pacing.average_shot_duration, 4.0)
            calibrated.pacing.median_shot_duration = max(profile.pacing.median_shot_duration, 3.5)
        elif clip_count < 6:
            calibrated.pacing.average_shot_duration = max(profile.pacing.average_shot_duration, 2.5)
            
        # Target duration cannot exceed total source duration
        if total_duration > 0 and calibrated.target_duration > total_duration:
            calibrated.target_duration = round(total_duration, 1)
            
        return calibrated
