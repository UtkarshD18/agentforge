import pytest
from pydantic import ValidationError
from agentforge_runtime.main import EditPlan, EditOperation
from agentforge_hosts import ResolveHostAdapter

def test_edit_plan_schema_validation():
    # 1. Verify schema accepts valid operations
    valid_op = EditOperation(
        type="select_segment",
        clip_id="IMG_0208.mov",
        start_frame=30,
        end_frame=60,
        reason="Panning shot"
    )
    assert valid_op.type == "select_segment"

    # 2. Verify schema rejects arbitrary code/python execution or unregistered operation types
    with pytest.raises(ValidationError):
        EditOperation(
            type="execute_python",
            clip_id="IMG_0208.mov",
            start_frame=0,
            end_frame=10,
            reason="Malicious code execution attempt"
        )

    with pytest.raises(ValidationError):
        EditOperation(
            type="delete_timeline",
            clip_id="IMG_0208.mov",
            start_frame=0,
            end_frame=10,
            reason="Malicious command attempt"
        )

def test_edit_plan_execution():
    # 3. Verify real-world playhead and marker mutations in Resolve via ResolveHostAdapter
    adapter = ResolveHostAdapter()
    resolve = adapter.connect_to_resolve()
    if resolve:
        try:
            p = resolve.GetProjectManager().GetCurrentProject()
            t1 = [p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount()+1) if p.GetTimelineByIndex(i).GetName() == 'Timeline 1'][0]
            p.SetCurrentTimeline(t1)
        except Exception:
            pass
            
    clips = adapter.get_timeline_clips()
    if not clips:
        pytest.skip("No timeline clips found to execute test.")
        
    clip = clips[0]
    
    # Test select_segment
    op_select = {
        "type": "select_segment",
        "clip_id": clip["name"],
        "start_frame": 10,
        "end_frame": 10,
        "reason": "Jump playhead test"
    }
    assert adapter.apply_operation(op_select, clip) is True
    
    # Test add_marker
    op_marker = {
        "type": "add_marker",
        "clip_id": clip["name"],
        "start_frame": 15,
        "end_frame": 15,
        "reason": "Transition point test"
    }
    assert adapter.apply_operation(op_marker, clip) is True
    
    # Verify the cyan marker is on the timeline
    resolve = adapter.connect_to_resolve()
    timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    markers = timeline.GetMarkers()
    
    # Calculate offset
    timeline_frame = int(clip["start_frame"] - clip["timeline_start_frame"] + (15 - clip["left_offset"]))
    assert timeline_frame in markers
    assert markers[timeline_frame]["color"] == "Cyan"
    assert markers[timeline_frame]["name"] == "GEMINI EDIT"
    
    # Cleanup Cyan marker
    timeline.DeleteMarkerByCustomData("agentforge-gemini-edit")
