import os
from typing import Dict, Any, List
from agentforge_video.ffmpeg import FFmpegWrapper
from agentforge_video.whisper import WhisperWrapper
from agentforge_core.workflow import TranscriptArtifact

class VideoPipeline:
    """
    Video Pipeline coordinator.
    Chains scene detection, keyframe extraction, and transcription tasks.
    """
    def __init__(self) -> None:
        self.ffmpeg = FFmpegWrapper()
        self.whisper = WhisperWrapper()

    def process_video(
        self,
        job_uri: str,
        task_uri: str,
        input_video_path: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Processes video to extract scenes, generate keyframes, and return transcript.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Transcribe audio track
        print(f"  - Starting audio transcription on: {input_video_path}")
        transcript: TranscriptArtifact = self.whisper.transcribe_audio(
            job_uri=job_uri,
            task_uri=task_uri,
            input_path=input_video_path
        )
        
        # 2. Segment scene time ranges
        print(f"  - Starting scene boundary detection...")
        scenes = self.ffmpeg.detect_scenes(input_video_path)
        
        # 3. Extract keyframe thumbnails at the midpoint of each scene segment
        keyframes: List[str] = []
        print(f"  - Starting keyframe extraction for {len(scenes)} scenes...")
        for idx, (start, end) in enumerate(scenes):
            midpoint = start + (end - start) / 2.0
            kf_name = f"scene_{idx}_frame.jpg"
            kf_path = os.path.join(output_dir, kf_name)
            
            try:
                self.ffmpeg.extract_keyframe(input_video_path, midpoint, kf_path)
                keyframes.append(kf_path)
            except Exception as e:
                print(f"⚠️ Failed to extract keyframe for scene {idx}: {e}")
                
        return {
            "scenes": scenes,
            "keyframes": keyframes,
            "transcript_uri": transcript.uri,
            "transcript_text": " ".join([seg.text for seg in transcript.segments])
        }
