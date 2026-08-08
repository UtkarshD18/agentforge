import sys
from resolve_smoke_test import connect_to_resolve

def run_integration_test() -> None:
    print("==================================================")
    print("🎬 Running DaVinci Resolve Unified Integration Test")
    print("==================================================")

    try:
        # 1. Connect
        resolve = connect_to_resolve()
        print("✓ Resolve scripting API connected.")

        # 2. Read project
        project_manager = resolve.GetProjectManager()
        assert project_manager is not None, "Failed to acquire ProjectManager."
        current_project = project_manager.GetCurrentProject()
        assert current_project is not None, "No active project open in Resolve."
        print(f"✓ Project verified: '{current_project.GetName()}'")

        # 3. Read timeline
        timeline = current_project.GetCurrentTimeline()
        assert timeline is not None, "No active timeline open in Resolve."
        print(f"✓ Timeline verified: '{timeline.GetName()}'")

        # 4. Create marker (frame 375)
        frame_id = 375
        marker_color = "Green"
        marker_name = "Integration Test"
        timeline.AddMarker(
            frameId=frame_id,
            color=marker_color,
            name=marker_name,
            note="Verified programmatically by unified test run.",
            duration=1
        )
        print(f"✓ Marker command dispatched to frame {frame_id}.")

        # 5. Verify marker exists
        markers = timeline.GetMarkers()
        assert markers is not None, "timeline.GetMarkers() returned None."
        assert frame_id in markers, f"Verification failed: Marker at frame {frame_id} was not found."
        assert markers[frame_id].get("color") == marker_color, "Verification failed: Marker color mismatch."
        print("✓ Marker creation verified via timeline.GetMarkers().")

        # 6. Jump frame (00:00:12:15)
        timecode = "00:00:12:15"
        timeline.SetCurrentTimecode(timecode)
        print(f"✓ Playhead set command dispatched to timecode {timecode}.")

        # 7. Verify playhead frame
        current_timecode = timeline.GetCurrentTimecode()
        assert current_timecode == timecode, f"Verification failed: Playhead at {current_timecode}, expected {timecode}."
        print("✓ Playhead navigation verified via timeline.GetCurrentTimecode().")

        # 8. Delete marker
        # Resolve scripting API deletion: timeline.DeleteMarkerAtFrame(frameId)
        success = timeline.DeleteMarkerAtFrame(frame_id)
        assert success, f"Failed to delete marker at frame {frame_id}."
        print(f"✓ Marker deletion command dispatched to frame {frame_id}.")

        # 9. Verify marker deletion
        markers_after_deletion = timeline.GetMarkers()
        assert frame_id not in markers_after_deletion, f"Verification failed: Marker at frame {frame_id} still exists."
        print("✓ Marker deletion verified via timeline.GetMarkers().")

        print("\n==================================================")
        print("🎉 INTEGRATION TEST PASS")
        print("==================================================")

    except AssertionError as ae:
        print(f"\n❌ ASSERTION FAILED: {ae}", file=sys.stderr)
        print("\nImplemented but not verified on live system (Resolve not running).", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as re:
        print(f"\n❌ ERROR: {re}", file=sys.stderr)
        print("\nImplemented but not verified on live system (Resolve not running).", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        print("\nImplemented but not verified on live system (Resolve not running).", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_integration_test()
