import pytest
from agentforge_hosts import ResolveHostAdapter

def test_resolve_edit_builder_and_auditor():
    adapter = ResolveHostAdapter()
    resolve = adapter.connect_to_resolve()
    if not resolve:
        pytest.skip("Resolve is offline or not running")

    # 1. Discover media pool and verify footage bin is found
    discovery = adapter.discover_media_pool()
    assert discovery["connected"] is True
    assert "footage" in discovery["bins"]
    
    footage_clips = discovery["bins"]["footage"]
    assert len(footage_clips) > 0
    
    # 2. Build mock EditPlan
    # We use clips present in the footage bin (e.g. IMG_0208.mov and IMG_0224.mov)
    clip_names = [c["name"] for c in footage_clips]
    clip1 = "IMG_0208.mov" if "IMG_0208.mov" in clip_names else clip_names[0]
    clip2 = "IMG_0224.mov" if "IMG_0224.mov" in clip_names else clip_names[0]
    
    edit_plan = [
        {
            "type": "insert_clip",
            "clip_id": clip1,
            "source_start": 10,
            "source_end": 70, # duration = 61 frames
            "reason": "Vlog opening sequence"
        },
        {
            "type": "insert_clip",
            "clip_id": clip2,
            "source_start": 30,
            "source_end": 70, # duration = 41 frames (within 0-79 bounds)
            "reason": "Vlog transition sequence"
        }
    ]
    
    target_timeline = "AgentForge_Vlog_Short_Test"
    
    # 3. Apply the EditPlan using the EditBuilder
    result = adapter.build_timeline_from_edit_plan(edit_plan, target_timeline_name=target_timeline)
    
    # 4. Verify success and timeline auditor matches
    assert result["success"] is True
    assert result["timeline_name"] == target_timeline
    
    audit = result["audit_results"]
    assert audit["expected_count"] == 2
    assert audit["actual_count"] == 2
    assert audit["audit_passed"] is True
    
    # Check individual item properties from the audit
    assert audit["items"][0]["actual_clip"] == clip1
    assert audit["items"][0]["actual_duration"] == 61
    assert audit["items"][0]["match"] is True
    
    assert audit["items"][1]["actual_clip"] == clip2
    assert audit["items"][1]["actual_duration"] == 41
    assert audit["items"][1]["match"] is True
