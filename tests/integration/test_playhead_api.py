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

    # Set playhead to 00:00:12:15
    timecode = "00:00:12:15"
    timeline.SetCurrentTimecode(timecode)
    
    # Verify change
    current_timecode = timeline.GetCurrentTimecode()
    assert current_timecode == timecode, f"Playhead at {current_timecode}, expected {timecode}."

    # Restore original state
    timeline.SetCurrentTimecode(original_timecode)
    restored_timecode = timeline.GetCurrentTimecode()
    assert restored_timecode == original_timecode, f"Playhead failed to restore to {original_timecode}."
