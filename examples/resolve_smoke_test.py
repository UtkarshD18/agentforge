import sys
import os

def connect_to_resolve():
    try:
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")
        if not resolve:
            raise RuntimeError("Resolve scripting object is None.")
        return resolve
    except ImportError:
        resolve_path = "/opt/resolve/libs"
        if resolve_path not in sys.path:
            sys.path.append(resolve_path)
            try:
                import DaVinciResolveScript as dvr_script
                resolve = dvr_script.scriptapp("Resolve")
                if resolve:
                    return resolve
            except ImportError:
                pass
        
        raise RuntimeError(
            "DaVinci Resolve scripting API is not accessible. "
            "Please ensure DaVinci Resolve is running and the environment variable "
            "PYTHONPATH includes '/opt/resolve/libs'."
        )
    except Exception as e:
        raise RuntimeError(f"Connection failed: {e}")

def main() -> None:
    print("==================================================")
    print("🎬 Running DaVinci Resolve Scripting API Smoke Test")
    print("==================================================")

    try:
        resolve = connect_to_resolve()
        print("✓ Connected to Resolve scripting API.")
        
        project_manager = resolve.GetProjectManager()
        assert project_manager is not None, "Failed to acquire Resolve ProjectManager."
        print("✓ Project Manager acquired.")
            
        current_project = project_manager.GetCurrentProject()
        assert current_project is not None, "No project is currently open in DaVinci Resolve."
        print(f"✓ Active Project verified: '{current_project.GetName()}'.")

        timeline = current_project.GetCurrentTimeline()
        assert timeline is not None, "No active timeline found in the current project."
        print(f"✓ Active Timeline verified: '{timeline.GetName()}'.")
        
        fps = timeline.GetSetting('timelineFrameRate')
        assert fps is not None, "Failed to read timeline frame rate setting."
        print(f"✓ Timeline FPS verified: {fps}")
        
        video_track_count = timeline.GetTrackCount("video")
        print(f"✓ Video track count verified: {video_track_count}")

        media_pool = current_project.GetMediaPool()
        assert media_pool is not None, "Failed to acquire project MediaPool."
        print("✓ Media Pool connection verified.")
        
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
