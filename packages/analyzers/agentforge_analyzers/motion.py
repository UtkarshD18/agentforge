import cv2
import numpy as np
import os
from typing import List, Dict, Any
from agentforge_analyzers.framework import BaseAnalyzer

class MotionAnalyzer(BaseAnalyzer):
    """
    Real pluggable MotionAnalyzer.
    Uses dense optical flow (Farneback) on raw media frames to detect camera movement direction and speed.
    Conforms to the BaseAnalyzer interface and has zero dependencies on DaVinci Resolve APIs.
    """
    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    @property
    def requires(self) -> List[str]:
        return ["video"]

    @property
    def produces(self) -> List[str]:
        return ["motion_events"]

    def run(self, graph_uri: str, input_path: str) -> None:
        # Implement the BaseAnalyzer interface if needed for pipeline execution
        pass

    def analyze_clip(self, input_path: str, fps: float = 30.0) -> List[Dict[str, Any]]:
        """
        Processes the target video file and returns a list of motion segments.
        Each segment contains: start_frame, end_frame, direction, magnitude, confidence.
        """
        if not os.path.exists(input_path):
            return []

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return []

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps and video_fps > 0:
            fps = video_fps

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return []

        # Sample frames at 2.0 FPS for processing speed
        sample_fps = 2.0
        sample_step = max(1, int(fps / sample_fps))

        prev_gray = None
        events = []
        current_event = None

        for frame_idx in range(0, total_frames, sample_step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            # Downscale frame to 160x120 for fast calculation
            small = cv2.resize(frame, (160, 120))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            if prev_gray is not None:
                # Calculate Farneback dense optical flow
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None,
                    pyr_scale=0.5, levels=1, winsize=15,
                    iterations=2, poly_n=5, poly_sigma=1.1,
                    flags=0
                )
                
                mean_dx = np.mean(flow[..., 0])
                mean_dy = np.mean(flow[..., 1])
                magnitude = np.sqrt(mean_dx**2 + mean_dy**2)

                direction = "static"
                if magnitude > self.threshold:
                    if abs(mean_dx) > abs(mean_dy):
                        direction = "right" if mean_dx > 0 else "left"
                    else:
                        direction = "down" if mean_dy > 0 else "up"

                confidence = min(0.99, float(0.5 + magnitude / 5.0))

                if direction != "static":
                    if current_event and current_event["direction"] == direction:
                        current_event["end_frame"] = frame_idx
                        current_event["magnitudes"].append(float(magnitude))
                        current_event["confidences"].append(confidence)
                    else:
                        if current_event:
                            events.append(self._finalize_event(current_event, fps))
                        current_event = {
                            "start_frame": frame_idx,
                            "end_frame": frame_idx,
                            "direction": direction,
                            "magnitudes": [float(magnitude)],
                            "confidences": [confidence]
                        }
                else:
                    if current_event:
                        events.append(self._finalize_event(current_event, fps))
                        current_event = None

            prev_gray = gray

        if current_event:
            events.append(self._finalize_event(current_event, fps))

        cap.release()
        return events

    def _finalize_event(self, event: Dict[str, Any], fps: float) -> Dict[str, Any]:
        avg_mag = float(np.mean(event["magnitudes"]))
        avg_conf = float(np.mean(event["confidences"]))
        return {
            "start_frame": event["start_frame"],
            "end_frame": event["end_frame"],
            "direction": event["direction"],
            "magnitude": round(avg_mag, 2),
            "confidence": round(avg_conf, 2),
            "start_seconds": round(event["start_frame"] / fps, 2),
            "end_seconds": round(event["end_frame"] / fps, 2)
        }
