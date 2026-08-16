import os
import sys
from typing import Any, Dict
from agentforge_hosts.base import HostAdapter, HostCapabilities, HostCommand

class ResolveHostAdapter(HostAdapter):
    """
    Real HostAdapter implementation for DaVinci Resolve.
    Connects to the live Resolve application via the remote scripting module.
    """
    def get_host_name(self) -> str:
        return "resolve"

    def get_capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            supports_timeline=True,
            supports_layers=False,
            supports_markers=True,
            supports_effects=False,
            supports_rendering=False,
            supports_undo=False
        )

    def connect_to_resolve(self) -> Any:
        """
        Dynamically connects to the running DaVinci Resolve scripting API.
        Appends installation paths to sys.path if not present.
        """
        try:
            import DaVinciResolveScript as dvr_script
            return dvr_script.scriptapp("Resolve")
        except ImportError:
            for path in ["/opt/resolve/libs", "/opt/resolve/Developer/Scripting/Modules"]:
                if path not in sys.path:
                    sys.path.append(path)
            try:
                import DaVinciResolveScript as dvr_script
                return dvr_script.scriptapp("Resolve")
            except Exception:
                return None
        except Exception:
            return None

    def get_timeline_clips(self) -> list:
        """
        Retrieves all timeline video clip metadata from the current Resolve project.
        """
        resolve = self.connect_to_resolve()
        if not resolve:
            return []
        try:
            pm = resolve.GetProjectManager()
            project = pm.GetCurrentProject()
            timeline = project.GetCurrentTimeline()
            if not timeline:
                return []
            
            items = timeline.GetItemListInTrack("video", 1) or []
            start_frame = timeline.GetStartFrame()
            fps_val = timeline.GetSetting('timelineFrameRate')
            fps = float(fps_val) if fps_val else 30.0

            clips_info = []
            for item in items:
                mp_item = item.GetMediaPoolItem()
                if not mp_item:
                    continue
                file_path = mp_item.GetClipProperty("File Path")
                if not file_path:
                    continue

                clips_info.append({
                    "name": item.GetName(),
                    "file_path": file_path,
                    "start_frame": item.GetStart(),
                    "end_frame": item.GetEnd(),
                    "left_offset": item.GetLeftOffset(),
                    "duration": item.GetDuration(),
                    "fps": fps,
                    "timeline_start_frame": start_frame
                })
            return clips_info
        except Exception:
            return []

    def add_marker(self, frame_offset: int, color: str, name: str, note: str, custom_data: str) -> bool:
        """
        Pushes an individual marker to the current timeline at the given frame offset.
        """
        resolve = self.connect_to_resolve()
        if not resolve:
            return False
        try:
            pm = resolve.GetProjectManager()
            project = pm.GetCurrentProject()
            timeline = project.GetCurrentTimeline()
            if not timeline:
                return False
            return timeline.AddMarker(frame_offset, color, name, note, 1, custom_data)
        except Exception:
            return False

    def execute_command(self, command: HostCommand) -> bool:
        """
        Executes commands in Resolve.
        Supports the 'test-control' command for Sprint 1.2 verification.
        """
        if command.command_id == "test-control":
            resolve = self.connect_to_resolve()
            if not resolve:
                command.parameters["results"] = {"error": "Could not connect to Resolve"}
                return False

            steps = {
                "read_playhead": "fail",
                "create_marker": "fail",
                "read_marker": "fail",
                "jump_playhead": "fail",
                "verify_playhead": "fail",
                "delete_marker": "fail",
                "restore_timeline": "fail"
            }
            command.parameters["results"] = steps

            timeline = None
            original_tc = None
            custom_data_val = "agentforge-test-1.2"

            try:
                pm = resolve.GetProjectManager()
                project = pm.GetCurrentProject()
                timeline = project.GetCurrentTimeline()
                if not timeline:
                    command.parameters["error"] = "No active timeline found in project."
                    return False

                # 1. Read playhead
                original_tc = timeline.GetCurrentTimecode()
                if not original_tc:
                    raise RuntimeError("Could not read original playhead timecode.")
                steps["read_playhead"] = "pass"

                start_frame = timeline.GetStartFrame()
                end_frame = timeline.GetEndFrame()
                fps_val = timeline.GetSetting('timelineFrameRate')
                fps = float(fps_val) if fps_val else 30.0

                # Helper conversions
                def timecode_to_frame(tc: str, rate: float) -> int:
                    parts = tc.split(':')
                    if len(parts) == 4:
                        h, m, s, f = map(int, parts)
                        return (h * 3600 + m * 60 + s) * int(rate) + f
                    return 0

                def frame_to_timecode(frame_num: int, rate: float) -> str:
                    total_seconds = int(frame_num // rate)
                    frames = int(frame_num % rate)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

                # Calculate target frame +5 seconds and clamp
                original_frame = timecode_to_frame(original_tc, fps)
                target_frame = original_frame + round(5 * fps)
                if target_frame >= end_frame:
                    target_frame = start_frame + 150  # Fallback offset if near end

                marker_offset = target_frame - start_frame

                # 2. Create marker
                success = timeline.AddMarker(
                    marker_offset,
                    "Green",
                    "AgentForge Test",
                    "Verification Marker",
                    1,
                    custom_data_val
                )
                if not success:
                    raise RuntimeError("Failed to add marker.")
                steps["create_marker"] = "pass"

                # 3. Read marker
                markers = timeline.GetMarkers()
                marker_found = False
                for key, val in markers.items():
                    if abs(float(key) - marker_offset) < 0.1 and val.get("customData") == custom_data_val:
                        marker_found = True
                        break
                if not marker_found:
                    raise RuntimeError("Marker not found in timeline list.")
                steps["read_marker"] = "pass"

                # 4. Jump playhead
                target_tc = frame_to_timecode(target_frame, fps)
                success_jump = timeline.SetCurrentTimecode(target_tc)
                if not success_jump:
                    raise RuntimeError("Failed to set current timecode.")
                steps["jump_playhead"] = "pass"

                # 5. Verify playhead
                new_tc = timeline.GetCurrentTimecode()
                if new_tc != target_tc:
                    raise RuntimeError(f"Playhead at {new_tc}, expected {target_tc}")
                steps["verify_playhead"] = "pass"

            except Exception as e:
                command.parameters["error"] = str(e)
                return False

            finally:
                # Guaranteed cleanup path
                if timeline:
                    # 6. Delete marker
                    try:
                        del_success = timeline.DeleteMarkerByCustomData(custom_data_val)
                        if del_success:
                            steps["delete_marker"] = "pass"
                    except Exception:
                        pass

                    # 7. Restore original playhead
                    if original_tc:
                        try:
                            restore_success = timeline.SetCurrentTimecode(original_tc)
                            if restore_success:
                                steps["restore_timeline"] = "pass"
                        except Exception:
                            pass

            return all(status == "pass" for status in steps.values())

        return False

    def apply_operation(self, op: Dict[str, Any], clip: Dict[str, Any]) -> bool:
        """
        Applies a validated edit plan operation to the DaVinci Resolve timeline.
        """
        resolve = self.connect_to_resolve()
        if not resolve:
            return False
        try:
            pm = resolve.GetProjectManager()
            project = pm.GetCurrentProject()
            timeline = project.GetCurrentTimeline()
            if not timeline:
                return False
                
            start_frame = clip["start_frame"]
            timeline_start_frame = clip["timeline_start_frame"]
            left_offset = clip["left_offset"]
            fps = clip["fps"]
            
            # Map start_frame relative to clip start back to absolute timeline frame
            op_start_frame = op["start_frame"]
            timeline_frame = int(start_frame - timeline_start_frame + (op_start_frame - left_offset))
            
            # Clamp to timeline 0-based offset bounds
            start_bound = timeline.GetStartFrame()
            end_bound = timeline.GetEndFrame()
            max_bound = end_bound - start_bound
            if timeline_frame < 0:
                timeline_frame = 0
            if timeline_frame >= max_bound:
                timeline_frame = max_bound - 1
                
            op_type = op["type"]
            reason = op["reason"]
            
            if op_type == "select_segment":
                # Convert frame back to timecode string
                def frame_to_timecode(frame_num: int, rate: float) -> str:
                    total_seconds = int(frame_num // rate)
                    frames = int(frame_num % rate)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                
                target_tc = frame_to_timecode(timeline_frame + timeline_start_frame, fps)
                return timeline.SetCurrentTimecode(target_tc)
                
            elif op_type == "add_marker":
                timeline.DeleteMarkerAtFrame(timeline_frame)
                return timeline.AddMarker(
                    timeline_frame,
                    "Cyan",
                    "GEMINI EDIT",
                    reason,
                    1,
                    "agentforge-gemini-edit"
                )
                
            elif op_type == "propose_trim":
                # Trim point is visually represented by a red marker
                timeline.DeleteMarkerAtFrame(timeline_frame)
                return timeline.AddMarker(
                    timeline_frame,
                    "Red",
                    "TRIM POINT",
                    f"Trim segment boundary: {reason}",
                    1,
                    "agentforge-gemini-edit"
                )
                
            return False
        except Exception:
            return False

    def discover_media_pool(self) -> Dict[str, Any]:
        """
        Discovers project bins and returns all clips grouped by subfolder name.
        """
        resolve = self.connect_to_resolve()
        if not resolve:
            return {"connected": False, "bins": {}}
            
        try:
            pm = resolve.GetProjectManager()
            project = pm.GetCurrentProject()
            mp = project.GetMediaPool()
            
            bins = {}
            for folder in mp.GetRootFolder().GetSubFolderList():
                folder_name = folder.GetName()
                clips = []
                for clip in folder.GetClipList():
                    clip_type = clip.GetClipProperty("Type")
                    if clip_type == "Timeline":
                        continue
                    clips.append({
                        "name": clip.GetName(),
                        "unique_id": clip.GetUniqueId(),
                        "fps": clip.GetClipProperty("FPS"),
                        "duration": clip.GetClipProperty("Duration"),
                        "frames": clip.GetClipProperty("Frames"),
                        "file_path": clip.GetClipProperty("File Path")
                    })
                bins[folder_name] = clips
                
            return {"connected": True, "bins": bins}
        except Exception as e:
            return {"connected": True, "bins": {}, "error": str(e)}

    def build_timeline_from_edit_plan(
        self,
        edit_plan: list[dict[str, Any]],
        target_timeline_name: str = "AgentForge_Vlog_Short_Test"
    ) -> Dict[str, Any]:
        """
        [APPLY MODE] Performs real timeline clip assembly, setting 9:16 vertical resolution,
        calculating dynamic aspect ratio zoom scaling, applying Pan/Tilt, and verifying.
        """
        resolve = self.connect_to_resolve()
        if not resolve:
            return {"success": False, "error": "Could not connect to Resolve"}

        try:
            pm = resolve.GetProjectManager()
            project = pm.GetCurrentProject()
            mp = project.GetMediaPool()

            # 1. Clean up existing target timeline if present
            timelines_to_delete = []
            for idx in range(1, project.GetTimelineCount() + 1):
                t = project.GetTimelineByIndex(idx)
                if t and t.GetName() == target_timeline_name:
                    timelines_to_delete.append(t)
            if timelines_to_delete:
                mp.DeleteTimelines(timelines_to_delete)

            # 2. Create target timeline and set active
            timeline = mp.CreateEmptyTimeline(target_timeline_name)
            if not timeline:
                return {"success": False, "error": f"Failed to create timeline: {target_timeline_name}"}
            project.SetCurrentTimeline(timeline)

            # 3. Configure 9:16 Vertical timeline resolution
            timeline.SetSetting('timelineUseCustomSettings', '1')
            timeline.SetSetting('timelineResolutionWidth', '1080')
            timeline.SetSetting('timelineResolutionHeight', '1920')

            # 4. Locate footage bin folder
            footage_folder = None
            for folder in mp.GetRootFolder().GetSubFolderList():
                if folder.GetName() == "footage":
                    footage_folder = folder
                    break
            if not footage_folder:
                return {"success": False, "error": "Could not find 'footage' folder in media pool"}

            # Map footage clips by name
            clip_registry = {c.GetName(): c for c in footage_folder.GetClipList()}

            # 5. Sequentially append marked/trimmed clips and apply transforms
            for op in edit_plan:
                op_type = op.get("type")
                if op_type == "insert_clip" or op_type == "trim_clip":
                    clip_id = op.get("clip_id")
                    if clip_id not in clip_registry:
                        continue
                    
                    clip = clip_registry[clip_id]
                    
                    # Read clip dimensions to determine scaling
                    res = clip.GetClipProperty("Resolution") or "1920x1080"
                    try:
                        w_str, h_str = res.split("x")
                        w, h = float(w_str), float(h_str)
                    except Exception:
                        w, h = 1920.0, 1080.0
                        
                    # Calculate dynamic zoom to fill vertical canvas without pillarboxes
                    default_zoom = (1920.0 * w) / (1080.0 * h) if w > h else 1.0
                    
                    transform = op.get("transform", {})
                    zoom_x = transform.get("zoom_x") or default_zoom
                    zoom_y = transform.get("zoom_y") or default_zoom
                    pan = transform.get("pan") or 0.0
                    tilt = transform.get("tilt") or 0.0
                    
                    start = op.get("source_start")
                    end = op.get("source_end")
                    
                    # Apply Non-Destructive In/Out Trims
                    clip.ClearMarkInOut()
                    if start is not None and end is not None:
                        clip.SetMarkInOut(start, end)
                        
                    mp.AppendToTimeline(clip)
                    import time
                    time.sleep(0.2)
                    clip.ClearMarkInOut()
                    
                    # Apply Layout Transformations to the newly appended item
                    items = timeline.GetItemListInTrack("video", 1) or []
                    if items:
                        last_item = items[-1]
                        last_item.SetProperty("ZoomX", float(zoom_x))
                        last_item.SetProperty("ZoomY", float(zoom_y))
                        last_item.SetProperty("Pan", float(pan * 1080.0))
                        last_item.SetProperty("Tilt", float(tilt * 1920.0))

                elif op_type in ["speed", "transition", "subtitle"]:
                    # Capability Gate: Explicitly return unsupported status
                    return {
                        "success": False,
                        "error": f"Operation '{op_type}' is requested but unsupported by this host adapter."
                    }

                elif op_type == "add_marker":
                    timeline_pos = op.get("timeline_position", 0)
                    timeline.AddMarker(
                        timeline_pos,
                        "Cyan",
                        "GEMINI EDIT",
                        op.get("reason", "Edit point"),
                        1,
                        "agentforge-gemini-edit"
                    )

            # 6. Timeline Auditor Step: Query Resolve timeline state and compare against plan
            actual_items = timeline.GetItemListInTrack("video", 1) or []
            expected_inserts = [op for op in edit_plan if op.get("type") in ["insert_clip", "trim_clip"]]

            audit_results = []
            audit_passed = len(actual_items) == len(expected_inserts)

            for i, expected_op in enumerate(expected_inserts):
                if i >= len(actual_items):
                    audit_passed = False
                    break
                
                actual_item = actual_items[i]
                expected_clip_id = expected_op.get("clip_id")
                expected_duration = expected_op.get("source_end") - expected_op.get("source_start") + 1
                
                actual_name = actual_item.GetName()
                actual_duration = actual_item.GetDuration()
                actual_zoom_x = actual_item.GetProperty("ZoomX")
                
                # Retrieve clip FPS from registry to calculate scaled duration
                clip_fps = 30.0
                if expected_clip_id in clip_registry:
                    try:
                        clip_fps = float(clip_registry[expected_clip_id].GetClipProperty("FPS") or 30.0)
                    except Exception:
                        pass
                        
                scaled_expected_duration = round(expected_duration * (30.0 / clip_fps))
                
                # Check for match (both duration with tolerance and clip name)
                name_match = (actual_name == expected_clip_id)
                dur_match = (abs(actual_duration - scaled_expected_duration) <= 2)
                match = name_match and dur_match
                if not match:
                    audit_passed = False

                audit_results.append({
                    "index": i,
                    "expected_clip": expected_clip_id,
                    "actual_clip": actual_name,
                    "expected_duration": expected_duration,
                    "scaled_expected_duration": scaled_expected_duration,
                    "actual_duration": actual_duration,
                    "actual_zoom_x": actual_zoom_x,
                    "match": match
                })

            return {
                "success": audit_passed,
                "timeline_name": target_timeline_name,
                "audit_results": {
                    "expected_count": len(expected_inserts),
                    "actual_count": len(actual_items),
                    "items": audit_results,
                    "audit_passed": audit_passed
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def render_timeline_to_file(
        self,
        target_timeline_name: str,
        output_path: str,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Executes a real rendering job for the target timeline using DaVinci Resolve.
        """
        resolve = self.connect_to_resolve()
        if not resolve:
            return {"success": False, "error": "Could not connect to Resolve"}

        try:
            import time
            pm = resolve.GetProjectManager()
            project = pm.GetCurrentProject()
            
            # Find and set active timeline
            target_timeline = None
            for idx in range(1, project.GetTimelineCount() + 1):
                t = project.GetTimelineByIndex(idx)
                if t and t.GetName() == target_timeline_name:
                    target_timeline = t
                    break
                    
            if not target_timeline:
                return {"success": False, "error": f"Timeline '{target_timeline_name}' not found."}
                
            project.SetCurrentTimeline(target_timeline)
            
            # Configure render settings
            out_dir = os.path.dirname(output_path)
            out_name = os.path.splitext(os.path.basename(output_path))[0]
            
            project.DeleteAllRenderJobs()
            
            # Load TikTok - 1080p preset to configure codecs and 9:16 layout natively
            try:
                project.LoadRenderPreset('TikTok - 1080p')
            except Exception:
                pass

            project.SetRenderSettings({
                "TargetDir": out_dir,
                "CustomName": out_name
            })
            
            job_id = project.AddRenderJob()
            if not job_id:
                return {"success": False, "error": "Failed to add render job in Resolve"}
                
            # Start rendering
            success = project.StartRendering(job_id)
            if not success:
                return {"success": False, "error": "Failed to start rendering job"}
                
            # Poll with timeout
            start_time = time.time()
            while project.IsRenderingInProgress():
                if time.time() - start_time > timeout_seconds:
                    project.StopRendering()
                    return {"success": False, "error": "RENDER_TIMEOUT"}
                time.sleep(0.5)
                
            # Verify file exists
            if not os.path.exists(output_path):
                # Search if Resolve exported with suffix or customized name in folder
                possible_path = os.path.join(out_dir, f"{out_name}.mp4")
                if os.path.exists(possible_path):
                    output_path = possible_path
                else:
                    return {"success": False, "error": "Render completed but output file was not found."}
                    
            return {
                "success": True,
                "output_path": output_path,
                "render_duration": round(time.time() - start_time, 2)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
