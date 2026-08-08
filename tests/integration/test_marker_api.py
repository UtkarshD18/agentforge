import pytest

pytestmark = pytest.mark.resolve

def test_resolve_marker_lifecycle(resolve_connection) -> None:
    project_manager = resolve_connection.GetProjectManager()
    current_project = project_manager.GetCurrentProject()
    assert current_project is not None, "No project open in DaVinci Resolve."

    timeline = current_project.GetCurrentTimeline()
    assert timeline is not None, "No active timeline found."

    # Add Marker at frame ID 375
    frame_id = 375
    timeline.AddMarker(
        frameId=frame_id,
        color="Green",
        name="AgentForge Test",
        note="Whip-pan camera shift transition location.",
        duration=1
    )
    
    # Read back markers and verify
    markers = timeline.GetMarkers()
    assert markers is not None
    assert frame_id in markers, f"Marker at frame {frame_id} was not created."
    
    # Clean up: Delete Marker
    success = timeline.DeleteMarkerAtFrame(frame_id)
    assert success, f"Failed to delete marker at frame {frame_id}."
    
    # Verify deletion
    markers_after = timeline.GetMarkers()
    assert frame_id not in markers_after, f"Marker at frame {frame_id} still exists after delete."
