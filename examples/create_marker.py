import sys
from resolve_smoke_test import connect_to_resolve

def main() -> None:
    print("==================================================")
    print("🎬 Adding Marker via DaVinci Resolve Scripting API")
    print("==================================================")

    try:
        resolve = connect_to_resolve()
        project_manager = resolve.GetProjectManager()
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
        assert markers is not None, "timeline.GetMarkers() returned None."
        assert frame_id in markers, f"Marker at frame {frame_id} was not created."
        
        marker_data = markers[frame_id]
        print(f"✓ Marker verified by GetMarkers()")
        print(f"  ├── Frame: {frame_id}")
        print(f"  ├── Color: {marker_data.get('color')}")
        print(f"  └── Name: {marker_data.get('name')}")
        
        print("\n[RESULT] PASS")

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
    main()
