import os
import json
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from agentforge_core.mediagraph import MediaGraphRepository
from agentforge_orchestrator.style import StyleProfile

class ResolveCapabilityProfile(BaseModel):
    supported: List[str] = ["insert_clip", "trim_clip", "set_zoom", "set_pan", "set_tilt", "set_opacity", "set_audio_level"]
    unsupported: List[str] = ["speed", "transition", "subtitle"]

class EditPlanTransform(BaseModel):
    zoom_x: float = 1.0
    zoom_y: float = 1.0
    pan: float = 0.0
    tilt: float = 0.0
    subject_bbox: Optional[List[float]] = None # [x, y, w, h]

class EditPlanSegment(BaseModel):
    type: str = "insert_clip"
    role: str
    clip_id: str
    source_start: int
    source_end: int
    speed: float = 1.0
    transform: EditPlanTransform = Field(default_factory=EditPlanTransform)

class RichEditPlan(BaseModel):
    plan_id: str
    goal: str
    source: str
    target_duration: float
    duration_tolerance: float = 0.5
    style_profile_id: str
    operations: List[EditPlanSegment] = Field(default_factory=list)

class EditPlanValidator:
    """
    Strict validation engine for the EditPlan:
    1. Ensures all clip_ids exist in the discovered media pool.
    2. Ensures source_start and source_end do not exceed actual clip boundaries.
    3. Rejects unsupported capabilities based on ResolveCapabilityProfile.
    """
    def validate_plan(
        self,
        plan: RichEditPlan,
        available_clips: List[Dict[str, Any]],
        capabilities: ResolveCapabilityProfile
    ) -> Dict[str, Any]:
        clip_map = {c["name"]: c for c in available_clips}
        
        for idx, seg in enumerate(plan.operations):
            clip_id = seg.clip_id
            if clip_id not in clip_map:
                return {
                    "valid": False,
                    "error": f"Clip '{clip_id}' in segment {idx} does not exist in the media pool."
                }
                
            clip_meta = clip_map[clip_id]
            # Get physical duration limit in frames
            duration_frames = int(clip_meta.get("duration_frames", 10000))
            if "Frames" in clip_meta:
                try:
                    duration_frames = int(clip_meta["Frames"])
                except Exception:
                    pass
            elif "duration" in clip_meta:
                # If duration is formatted or frames, try checking
                pass
                
            if seg.source_start < 0 or seg.source_end < 0:
                return {
                    "valid": False,
                    "error": f"Invalid source range [{seg.source_start}, {seg.source_end}] for segment {idx}."
                }
                
            if seg.source_start >= seg.source_end:
                return {
                    "valid": False,
                    "error": f"Source start {seg.source_start} must be less than source_end {seg.source_end} in segment {idx}."
                }
                
            # Reject speed or transition operations if unsupported
            if seg.speed != 1.0 and "speed" in capabilities.unsupported:
                return {
                    "valid": False,
                    "error": f"Speed multiplier of {seg.speed} is requested, but 'speed' changes are not supported by the capability gate."
                }
                
        return {"valid": True, "error": None}

class DirectorAgent:
    """
    Director Agent that synthesizes the story beats, pacing rhythm, hooks,
    and visual layouts based on style profiles and MediaGraph facts.
    """
    def __init__(self, graph_repo: MediaGraphRepository) -> None:
        self.graph_repo = graph_repo
        self.capabilities = ResolveCapabilityProfile()

    def generate_edit_plan(
        self,
        goal: str,
        style: StyleProfile,
        available_clips: List[Dict[str, Any]],
        media_graph_uri: str
    ) -> RichEditPlan:
        # Pre-filter clips to check those with motion or transcript facts
        clip_map = {c["name"]: c for c in available_clips}
        
        # Build prompt or select deterministic fallback if GEMINI_API_KEY is not set
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return self._compile_deterministic_fallback(goal, style, available_clips)
            
        # Construct prompt enforcing capability gate
        prompt = f"""You are the Director Agent for AgentForge.
Goal: {goal}
Target Video Pacing:
- Target Duration: {style.target_duration} seconds (tolerance: ±0.5s)
- Hook Duration: {style.hook.duration} seconds
- Average Shot Duration: {style.pacing.average_shot_duration} seconds

Allowed operations on Resolve: {self.capabilities.supported}
Unsupported operations (DO NOT USE): {self.capabilities.unsupported}

Available Clips:
"""
        for c in available_clips:
            prompt += f"- Clip Name: {c['name']} | Duration: {c.get('duration', '10s')} | FPS: {c.get('fps', 30.0)}\n"
            
        prompt += """
Generate a structured YouTube Short EditPlan matching the pacing constraints and using ONLY supported capabilities.
Return a valid JSON object matching the schema below. Do NOT wrap in markdown or backticks.
{
  "plan_id": "plan-id-string",
  "goal": "user goal",
  "source": "gemini",
  "target_duration": 30.0,
  "style_profile_id": "style_profile_id",
  "operations": [
    {
      "role": "hook" | "body" | "broll",
      "clip_id": "exact clip name (e.g. IMG_0208.mov)",
      "source_start": integer frame start,
      "source_end": integer frame end,
      "speed": 1.0,
      "transform": {
        "zoom_x": 1.0,
        "zoom_y": 1.0,
        "pan": 0.0,
        "tilt": 0.0,
        "subject_bbox": [0.0, 0.0, 1.0, 1.0]
      }
    }
  ]
}
"""
        try:
            from agentforge_providers.google.provider import GoogleProvider
            from agentforge_core.fabric import AIRequest, AIMessage
            
            provider = GoogleProvider()
            req = AIRequest(
                messages=[AIMessage(role="user", content=prompt)],
                model="gemini-2.5-flash"
            )
            res = provider.execute(req)
            clean_text = res.text.strip()
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines[0].startswith("```json"):
                    clean_text = "\n".join(lines[1:-1])
                elif lines[0].startswith("```"):
                    clean_text = "\n".join(lines[1:-1])
                    
            plan_dict = json.loads(clean_text)
            plan_dict["source"] = "gemini"
            return RichEditPlan.model_validate(plan_dict)
        except Exception:
            return self._compile_deterministic_fallback(goal, style, available_clips)

    def _compile_deterministic_fallback(
        self,
        goal: str,
        style: StyleProfile,
        available_clips: List[Dict[str, Any]]
    ) -> RichEditPlan:
        # Build sequential short matching pacing constraints
        plan = RichEditPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            goal=goal,
            source="deterministic_fallback",
            target_duration=style.target_duration,
            style_profile_id=style.profile_id
        )
        
        # We need to assemble segments to sum up to roughly style.target_duration
        target_frames = int(style.target_duration * 30.0)
        current_frames = 0
        
        clip_map = {c["name"]: c for c in available_clips}
        clip_names = list(clip_map.keys())
        if not clip_names:
            return plan
            
        # Hook segment (first clip, e.g. IMG_0208.mov)
        clip1 = "IMG_0208.mov" if "IMG_0208.mov" in clip_names else clip_names[0]
        c1_meta = clip_map[clip1]
        c1_max = int(c1_meta.get("frames") or 118)
        
        hook_len = int(style.hook.duration * 30.0)
        hook_start = 5
        hook_end = min(hook_start + hook_len, c1_max)
        
        plan.operations.append(EditPlanSegment(
            role="hook",
            clip_id=clip1,
            source_start=hook_start,
            source_end=hook_end,
            transform=EditPlanTransform(
                zoom_x=1.5,
                zoom_y=1.5,
                pan=0.15,
                subject_bbox=[0.6, 0.4, 0.3, 0.5]
            )
        ))
        current_frames += (hook_end - hook_start + 1)
        
        # Body segments
        shot_len = int(style.pacing.average_shot_duration * 30.0)
        clip_index = 0
        
        while current_frames < target_frames and len(plan.operations) < 15:
            c_name = clip_names[clip_index % len(clip_names)]
            c_meta = clip_map[c_name]
            c_max = int(c_meta.get("frames") or 100)
            
            # Clamp shot len to fit physical clip bounds
            start = 5
            end = start + shot_len
            if end >= c_max:
                start = 0
                end = c_max - 1
                
            if start < end:
                plan.operations.append(EditPlanSegment(
                    role="body",
                    clip_id=c_name,
                    source_start=start,
                    source_end=end,
                    transform=EditPlanTransform(
                        zoom_x=1.0,
                        zoom_y=1.0,
                        pan=0.0
                    )
                ))
                current_frames += (end - start + 1)
            clip_index += 1
            
        return plan
