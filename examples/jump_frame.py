import sys
from resolve_smoke_test import connect_to_resolve

def main() -> None:
    print("==================================================")
    print("🎬 Jumping Playhead via DaVinci Resolve Scripting API")
    print("==================================================")

    try:
        resolve = connect_to_resolve()
        project_manager = resolve.GetProjectManager()
        current_project = project_manager.GetCurrentProject()
        assert current_project is not None, "No project open in DaVinci Resolve."

        timeline = current_project.GetCurrentTimeline()
        assert timeline is not None, "No active timeline found."

        # Set playhead position to 00:00:12:15
        timecode = "00:00:12:15"
        timeline.SetCurrentTimecode(timecode)
        
        # Read playhead timecode and verify
        current_timecode = timeline.GetCurrentTimecode()
        assert current_timecode == timecode, f"Playhead navigation failed. Expected {timecode}, read {current_timecode}"
        
        print(f"✓ Playhead focus verified by GetCurrentTimecode()")
        print(f"  └── Timecode: {current_timecode}")
        
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
