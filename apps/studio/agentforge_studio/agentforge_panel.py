import sys
import json
import time
import urllib.request
import urllib.error

# Resolve UIManager layout script
# When run from DaVinci Resolve, 'resolve', 'fusion', and 'bmd' are globally defined.
try:
    resolve_app = resolve
    fusion_app = fusion
except NameError:
    try:
        import DaVinciResolveScript as dvr_script
        resolve_app = dvr_script.scriptapp("Resolve")
        fusion_app = resolve_app.GetFusion()
    except Exception:
        resolve_app = None
        fusion_app = None

# If not running inside DaVinci Resolve script utility environment
if not resolve_app or not fusion_app:
    print("Error: This script must be run from inside DaVinci Resolve's Scripts utility environment.")
    sys.exit(1)

ui = fusion_app.UIManager
disp = bmd.UIDispatcher(ui)

# Create layout
dlg = disp.AddWindow({
    "WindowTitle": "AgentForge OS Panel",
    "ID": "AFWin",
    "Geometry": [200, 200, 420, 320],
}, [
    ui.VGroup([
        # Status Block
        ui.HGroup([
            ui.Label({"Text": "AgentForge Engine: ", "Weight": 0}),
            ui.Label({"ID": "DaemonStatus", "Text": "🔴 Daemon Offline", "Weight": 1}),
        ]),
        
        ui.HGroup([
            ui.Label({"Text": "Resolve Status: ", "Weight": 0}),
            ui.Label({"ID": "ResolveStatus", "Text": "🟢 Connected", "Weight": 1}),
        ]),
        
        # Divider line
        ui.Label({"Text": "──────────────────────────────────────────"}),
        
        # Project Info
        ui.HGroup([
            ui.Label({"Text": "Project Name: ", "Weight": 0}),
            ui.Label({"ID": "ProjName", "Text": "None", "Weight": 1}),
        ]),
        ui.HGroup([
            ui.Label({"Text": "Active Timeline: ", "Weight": 0}),
            ui.Label({"ID": "TimelineName", "Text": "None", "Weight": 1}),
        ]),
        ui.HGroup([
            ui.Label({"Text": "Timeline FPS: ", "Weight": 0}),
            ui.Label({"ID": "TimelineFPS", "Text": "0.0", "Weight": 1}),
        ]),
        ui.HGroup([
            ui.Label({"Text": "Clip Count: ", "Weight": 0}),
            ui.Label({"ID": "ClipCount", "Text": "0", "Weight": 1}),
        ]),
        
        ui.Label({"Text": "──────────────────────────────────────────"}),
        
        # Sync and action buttons
        ui.HGroup([
            ui.Button({"ID": "SyncBtn", "Text": "🔄 Refresh Metadata"}),
            ui.Button({"ID": "AnalyzeBtn", "Text": "🎬 Analyze Timeline"}),
        ]),
    ])
])

itm = dlg.GetItems()

def post_session_to_daemon(project_name, timeline_name, fps, clip_count):
    """Sends the active state snapshot to the localhost FastAPI daemon."""
    url = "http://localhost:8080/api/v1/hosts/resolve/session"
    data = {
        "host": "resolve",
        "connected": True,
        "project": {"name": project_name},
        "timeline": {
            "name": timeline_name,
            "fps": float(fps),
            "start_frame": 0,
            "end_frame": 0,
            "clip_count": int(clip_count)
        },
        "source": "resolve",
        "updated_at": time.time()
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=1.0) as response:
            return response.status == 200 or response.status == 201
    except Exception:
        return False

def refresh_metrics():
    """Queries live Resolve properties and updates the UI."""
    try:
        project_manager = resolve_app.GetProjectManager()
        project = project_manager.GetCurrentProject()
        if not project:
            itm["ProjName"].Text = "No project open"
            itm["TimelineName"].Text = "None"
            itm["TimelineFPS"].Text = "0.0"
            itm["ClipCount"].Text = "0"
            return
            
        project_name = project.GetName()
        itm["ProjName"].Text = project_name
        
        timeline = project.GetCurrentTimeline()
        if not timeline:
            itm["TimelineName"].Text = "No active timeline"
            itm["TimelineFPS"].Text = "0.0"
            itm["ClipCount"].Text = "0"
            return
            
        timeline_name = timeline.GetName()
        itm["TimelineName"].Text = timeline_name
        
        fps = timeline.GetSetting('timelineFrameRate')
        itm["TimelineFPS"].Text = str(fps) if fps else "0.0"
        
        # Count clips in active video tracks
        total_clips = 0
        video_tracks = timeline.GetTrackCount("video")
        for track_idx in range(1, int(video_tracks) + 1):
            items = timeline.GetItemListInTrack("video", track_idx)
            if items:
                total_clips += len(items)
                
        itm["ClipCount"].Text = str(total_clips)
        
        # Post snapshot state to daemon
        success = post_session_to_daemon(project_name, timeline_name, fps or 0.0, total_clips)
        if success:
            itm["DaemonStatus"].Text = "🟢 Connected"
        else:
            itm["DaemonStatus"].Text = "🔴 Daemon Offline"
            
    except Exception as e:
        print(f"Error querying Resolve metrics: {e}")
        itm["DaemonStatus"].Text = "🔴 Error Querying API"

# Event Handlers
def _close_event(ev):
    disp.ExitLoop()

def _sync_clicked(ev):
    refresh_metrics()

def _analyze_clicked(ev):
    print("Analyze timeline triggered.")
    url = "http://localhost:8080/api/v1/workspace"
    req = urllib.request.Request(
        url,
        data=json.dumps({"name": "Nike Vlog Short #1", "metadata": {}}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=1.0)
        print("Analysis task queued successfully.")
    except Exception as e:
        print(f"Failed to query daemon: {e}")

# Attach Event handlers
dlg.On.AFWin.Close = _close_event
dlg.On.SyncBtn.Clicked = _sync_clicked
dlg.On.AnalyzeBtn.Clicked = _analyze_clicked

# Populate UI on startup
refresh_metrics()

# Display and loop
dlg.Show()
disp.RunLoop()
dlg.Hide()
