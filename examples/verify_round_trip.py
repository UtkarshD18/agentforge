import sys
import os
import json
import time
import urllib.request

def connect_to_resolve():
    try:
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")
        if not resolve:
            raise RuntimeError("Resolve scripting object is None.")
        return resolve
    except ImportError:
        resolve_path = "/opt/resolve/Developer/Scripting/Modules"
        if resolve_path not in sys.path:
            sys.path.append(resolve_path)
            try:
                import DaVinciResolveScript as dvr_script
                resolve = dvr_script.scriptapp("Resolve")
                if resolve:
                    return resolve
            except ImportError:
                pass
        raise RuntimeError("DaVinci Resolve scripting API is not accessible.")

def main():
    print("==================================================")
    print("🔄 Running Real-World Resolve -> Daemon Round Trip")
    print("==================================================")

    # 1. Connect to Resolve
    try:
        resolve = connect_to_resolve()
        print("✓ Connected to Resolve scripting API.")
    except Exception as e:
        print(f"❌ Failed to connect to Resolve: {e}")
        sys.exit(1)

    # 2. Extract Active State
    try:
        project_manager = resolve.GetProjectManager()
        current_project = project_manager.GetCurrentProject()
        if not current_project:
            print("❌ No project open in Resolve.")
            sys.exit(1)
        project_name = current_project.GetName()
        print(f"✓ Active Project: '{project_name}'")

        timeline = current_project.GetCurrentTimeline()
        if not timeline:
            print("❌ No active timeline in Resolve.")
            sys.exit(1)
        timeline_name = timeline.GetName()
        print(f"✓ Active Timeline: '{timeline_name}'")

        fps = timeline.GetSetting('timelineFrameRate')
        fps_val = float(fps) if fps else 0.0
        print(f"✓ Timeline FPS: {fps_val}")

        total_clips = 0
        video_tracks = timeline.GetTrackCount("video")
        for track_idx in range(1, int(video_tracks) + 1):
            items = timeline.GetItemListInTrack("video", track_idx)
            if items:
                total_clips += len(items)
        print(f"✓ Video Clips Count: {total_clips}")

    except Exception as e:
        print(f"❌ Failed to extract Resolve metadata: {e}")
        sys.exit(1)

    # 3. POST to Daemon
    daemon_base = "http://127.0.0.1:8888"
    session_url = f"{daemon_base}/api/v1/hosts/resolve/session"
    
    payload = {
        "host": "resolve",
        "connected": True,
        "project": {"name": project_name},
        "timeline": {
            "name": timeline_name,
            "fps": fps_val,
            "start_frame": 0,
            "end_frame": 0,
            "clip_count": total_clips
        },
        "source": "resolve",
        "updated_at": time.time()
    }

    print(f"\nSending payload to Daemon at {session_url}...")
    req = urllib.request.Request(
        session_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                print("✓ POST success (200 OK)")
            else:
                print(f"❌ POST failed with status: {resp.status}")
                sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to POST to daemon: {e}")
        sys.exit(1)

    # 4. GET from Daemon to Verify Round Trip
    print(f"Retrieving active session from Daemon at {session_url}...")
    req_get = urllib.request.Request(session_url, method="GET")
    try:
        with urllib.request.urlopen(req_get, timeout=2.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                print("✓ GET success (200 OK)")
                print("\n================== VERIFICATION ==================")
                print(f"Expected Project:  '{project_name}'")
                print(f"Returned Project:  '{data['project']['name']}'")
                print(f"Expected Timeline: '{timeline_name}'")
                print(f"Returned Timeline: '{data['timeline']['name']}'")
                print(f"Expected FPS:      {fps_val}")
                print(f"Returned FPS:      {data['timeline']['fps']}")
                print(f"Expected Clips:    {total_clips}")
                print(f"Returned Clips:    {data['timeline']['clip_count']}")
                print("==================================================")
                
                # Assertions
                assert data['project']['name'] == project_name
                assert data['timeline']['name'] == timeline_name
                assert data['timeline']['fps'] == fps_val
                assert data['timeline']['clip_count'] == total_clips
                print("\n🎉 [ROUND TRIP SUCCESS] Panel state successfully synchronized with Daemon!")
            else:
                print(f"❌ GET failed with status: {resp.status}")
                sys.exit(1)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
