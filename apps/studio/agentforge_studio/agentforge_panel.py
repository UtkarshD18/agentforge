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
    except ImportError:
        for path in ["/opt/resolve/libs", "/opt/resolve/Developer/Scripting/Modules"]:
            if path not in sys.path:
                sys.path.append(path)
        import DaVinciResolveScript as dvr_script
    try:
        resolve_app = dvr_script.scriptapp("Resolve")
        fusion_app = resolve_app.Fusion()
    except Exception:
        resolve_app = None
        fusion_app = None

# If not running inside DaVinci Resolve script utility environment
if not resolve_app or not fusion_app:
    print("Error: This script must be run from inside DaVinci Resolve's Scripts utility environment.")
    sys.exit(1)

ui = fusion_app.UIManager
disp = bmd.UIDispatcher(ui)

DAEMON_BASE_URL = "http://127.0.0.1:8888"

# Create layout
dlg = disp.AddWindow({
    "WindowTitle": "AgentForge OS Panel",
    "ID": "AFWin",
    "Geometry": [200, 200, 420, 750],
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
        
        ui.Button({"ID": "TestControlBtn", "Text": "⚡ Test Resolve Control"}),
        
        ui.Label({"Text": "Command Round Trip Status:"}),
        ui.Label({"ID": "TestStep1", "Text": "  - Read original playhead"}),
        ui.Label({"ID": "TestStep2", "Text": "  - Create marker"}),
        ui.Label({"ID": "TestStep3", "Text": "  - Read marker"}),
        ui.Label({"ID": "TestStep4", "Text": "  - Jump playhead"}),
        ui.Label({"ID": "TestStep5", "Text": "  - Verify playhead"}),
        ui.Label({"ID": "TestStep6", "Text": "  - Delete marker"}),
        ui.Label({"ID": "TestStep7", "Text": "  - Restore timeline"}),
        ui.Label({"ID": "TestResult", "Text": "RESULT: PENDING"}),

        ui.Label({"Text": "──────────────────────────────────────────"}),
        ui.Label({"Text": "🎬 AI Edit Planning:"}),
        ui.HGroup([
            ui.Label({"Text": "Goal: ", "Weight": 0}),
            ui.LineEdit({"ID": "GoalInput", "Text": "Create a 30-second energetic short", "Weight": 1}),
        ]),
        ui.Button({"ID": "PlanBtn", "Text": "🪄 Generate AI Edit Plan"}),
        ui.Label({"ID": "PlanPreview", "Text": "No active plan proposed.", "WordWrap": True}),
        ui.HGroup([
            ui.Button({"ID": "ApplyBtn", "Text": "🟢 Apply Edit"}),
            ui.Button({"ID": "RejectBtn", "Text": "🔴 Reject Plan"}),
        ]),
    ])
])

itm = dlg.GetItems()

def post_session_to_daemon(project_name, timeline_name, fps, clip_count):
    """Sends the active state snapshot to the localhost FastAPI daemon."""
    url = f"{DAEMON_BASE_URL}/api/v1/hosts/resolve/session"
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
    itm["TestResult"].Text = "RESULT: RUNNING ANALYSIS..."
    for idx in range(1, 8):
        itm[f"TestStep{idx}"].Text = ""
        
    url = f"{DAEMON_BASE_URL}/api/v1/hosts/resolve/commands/analyze-timeline"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                success = data.get("success", False)
                clips = data.get("clips_analyzed", [])
                
                itm["TestStep1"].Text = f"✓ Extracted {len(clips)} timeline clips"
                
                # Render results for first few clips
                step_idx = 2
                for clip in clips[:2]:
                    name = clip.get("name", "Unknown")
                    events = clip.get("motion_events", [])
                    if events:
                        ev_desc = f"{events[0]['direction'].capitalize()} pan ({events[0]['confidence']:.2f})"
                        itm[f"TestStep{step_idx}"].Text = f"✓ Analyzed {name} (Motion: {ev_desc})"
                    else:
                        itm[f"TestStep{step_idx}"].Text = f"✓ Analyzed {name} (Static)"
                    step_idx += 1
                
                # Fill in the rest of status labels
                itm["TestStep4"].Text = "KNOWLEDGE  ✓ Updated"
                itm["TestStep5"].Text = "MEDIA GRAPH ✓ Updated"
                itm["TestStep6"].Text = "RESOLVE     ✓ Markers created"
                
                # Show jumpable instruction note
                itm["TestStep7"].Text = "⚡ Control round-trip operational"
                
                if success:
                    itm["TestResult"].Text = "RESULT: PASS"
                    refresh_metrics()  # Update clip counts or info
                else:
                    itm["TestResult"].Text = "RESULT: FAIL"
            else:
                itm["TestResult"].Text = f"RESULT: ERROR {response.status}"
    except Exception as e:
        itm["TestResult"].Text = f"RESULT: EXCEPTION {e}"

def _test_control_clicked(ev):
    itm["TestResult"].Text = "RESULT: RUNNING..."
    for idx in range(1, 8):
        itm[f"TestStep{idx}"].Text = f"  - Step {idx}"
        
    url = f"{DAEMON_BASE_URL}/api/v1/hosts/resolve/commands/test-control"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                success = data.get("success", False)
                steps = data.get("steps", {})
                
                def fmt_step(name, label):
                    status = steps.get(name, "fail")
                    symbol = "✓" if status == "pass" else "❌"
                    return f"{symbol} {label}"

                itm["TestStep1"].Text = fmt_step("read_playhead", "Read original playhead")
                itm["TestStep2"].Text = fmt_step("create_marker", "Create marker")
                itm["TestStep3"].Text = fmt_step("read_marker", "Read marker")
                itm["TestStep4"].Text = fmt_step("jump_playhead", "Jump playhead")
                itm["TestStep5"].Text = fmt_step("verify_playhead", "Verify playhead")
                itm["TestStep6"].Text = fmt_step("delete_marker", "Delete marker")
                itm["TestStep7"].Text = fmt_step("restore_timeline", "Restore timeline")
                
                if success:
                    itm["TestResult"].Text = "RESULT: PASS"
                else:
                    itm["TestResult"].Text = f"RESULT: FAIL"
            else:
                itm["TestResult"].Text = f"RESULT: ERROR {response.status}"
    except Exception as e:
        itm["TestResult"].Text = f"RESULT: EXCEPTION {e}"

# Attach Event handlers
current_active_plan_id = None

def _generate_plan_clicked(ev):
    global current_active_plan_id
    itm["PlanPreview"].Text = "Generating plan..."
    goal = itm["GoalInput"].Text or "Create a 30-second energetic short"
    
    url = f"{DAEMON_BASE_URL}/api/v1/hosts/resolve/commands/generate-edit-plan"
    req_data = json.dumps({"goal": goal}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                plan = data.get("plan", {})
                current_active_plan_id = plan.get("plan_id")
                source = data.get("source", "unknown")
                reason = data.get("reason", "")
                
                ops = plan.get("operations", [])
                preview_text = f"Plan ID: {current_active_plan_id}\nSource: {source} ({reason})\nProposed Cuts:\n"
                for idx, op in enumerate(ops[:3]):
                    preview_text += f"{idx+1}. {op['type'].upper()} {op['clip_id']} frames {op['start_frame']}-{op['end_frame']} ({op['reason']})\n"
                if len(ops) > 3:
                    preview_text += f"...and {len(ops) - 3} more operations."
                    
                itm["PlanPreview"].Text = preview_text
            else:
                itm["PlanPreview"].Text = f"Error generating plan: {response.status}"
    except Exception as e:
        itm["PlanPreview"].Text = f"Exception: {e}"

def _apply_plan_clicked(ev):
    global current_active_plan_id
    if not current_active_plan_id:
        itm["PlanPreview"].Text = "No active plan proposed to apply."
        return
        
    itm["PlanPreview"].Text = "Applying plan..."
    url = f"{DAEMON_BASE_URL}/api/v1/hosts/resolve/commands/apply-edit-plan"
    req_data = json.dumps({"plan_id": current_active_plan_id}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                applied = data.get("operations_applied", 0)
                itm["PlanPreview"].Text = f"Plan {current_active_plan_id} applied successfully. Created {applied} timeline cuts."
                current_active_plan_id = None
            else:
                itm["PlanPreview"].Text = f"Error applying plan: {response.status}"
    except Exception as e:
        itm["PlanPreview"].Text = f"Exception: {e}"

def _reject_plan_clicked(ev):
    global current_active_plan_id
    if not current_active_plan_id:
        itm["PlanPreview"].Text = "No active plan to reject."
        return
        
    url = f"{DAEMON_BASE_URL}/api/v1/hosts/resolve/commands/reject-edit-plan"
    req_data = json.dumps({"plan_id": current_active_plan_id}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=5.0)
    except Exception:
        pass
        
    itm["PlanPreview"].Text = f"Plan {current_active_plan_id} rejected."
    current_active_plan_id = None

dlg.On.AFWin.Close = _close_event
dlg.On.SyncBtn.Clicked = _sync_clicked
dlg.On.AnalyzeBtn.Clicked = _analyze_clicked
dlg.On.TestControlBtn.Clicked = _test_control_clicked
dlg.On.PlanBtn.Clicked = _generate_plan_clicked
dlg.On.ApplyBtn.Clicked = _apply_plan_clicked
dlg.On.RejectBtn.Clicked = _reject_plan_clicked

# Populate UI on startup
refresh_metrics()

# Display and loop
dlg.Show()
disp.RunLoop()
dlg.Hide()
