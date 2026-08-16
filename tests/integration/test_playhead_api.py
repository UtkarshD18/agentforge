import pytest

pytestmark = pytest.mark.resolve

def test_resolve_playhead_navigation(resolve_connection) -> None:
    project_manager = resolve_connection.GetProjectManager()
    current_project = project_manager.GetCurrentProject()
    assert current_project is not None, "No project open in DaVinci Resolve."

    timeline = current_project.GetCurrentTimeline()
    assert timeline is not None, "No active timeline found."

    # Record current playhead to restore original state
    original_timecode = timeline.GetCurrentTimecode()

    # Calculate target timecode (+10s relative to start frame)
    fps_val = timeline.GetSetting('timelineFrameRate')
    fps = float(fps_val) if fps_val else 30.0
    start_f = timeline.GetStartFrame()
    target_f = start_f + int(10 * fps)

    def frame_to_timecode(frame_num: int, rate: float) -> str:
        total_seconds = int(frame_num // rate)
        frames = int(frame_num % rate)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

    timecode = frame_to_timecode(target_f, fps)
    timeline.SetCurrentTimecode(timecode)
    
    # Verify change
    current_timecode = timeline.GetCurrentTimecode()
    assert current_timecode == timecode, f"Playhead at {current_timecode}, expected {timecode}."

    # Restore original state
    timeline.SetCurrentTimecode(original_timecode)
    restored_timecode = timeline.GetCurrentTimecode()
    assert restored_timecode == original_timecode, f"Playhead failed to restore to {original_timecode}."
