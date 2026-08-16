import time
import hashlib
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from agentforge_core.mediagraph import MediaGraphRepository, TemporalNode, SemanticNode, MediaNodeProvenance

class CrystallizedFact(BaseModel):
    fact_id: str
    type: str  # e.g., "scene", "subject", "camera_motion", "usable_segment"
    value: Any
    confidence: float
    source_nodes: List[str]
    source_media_hash: str
    source_model: str
    model_version: str
    created_at: float = Field(default_factory=time.time)
    analysis_parameters_hash: str

class KnowledgeCrystallizer:
    """
    Deterministically merges raw observations (optical flow, silence, OCR, Whisper transcripts)
    into distilled high-level facts saved in the MediaGraph database.
    """
    def __init__(self, graph_repo: MediaGraphRepository) -> None:
        self.graph_repo = graph_repo

    def crystallize_and_save(
        self,
        media_graph_uri: str,
        clip_name: str,
        media_hash: str,
        raw_observations: List[Dict[str, Any]],
        model_name: str,
        model_version: str,
        params: Dict[str, Any]
    ) -> List[CrystallizedFact]:
        facts = []
        
        # Calculate params hash
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode("utf-8")).hexdigest()[:16]

        # 1. Deterministic visual energy consolidation from motion observations
        motion_obs = [o for o in raw_observations if o.get("type") == "motion"]
        if motion_obs:
            peak_motion = max([o.get("energy", 0.0) for o in motion_obs])
            avg_motion = sum([o.get("energy", 0.0) for o in motion_obs]) / len(motion_obs)
            source_nodes = [o.get("uri") for o in motion_obs if "uri" in o]
            
            fact = CrystallizedFact(
                fact_id=f"fact://clip/{clip_name.replace('.', '_')}/visual_energy",
                type="visual_energy",
                value={"peak": peak_motion, "average": avg_motion},
                confidence=0.90,
                source_nodes=source_nodes,
                source_media_hash=media_hash,
                source_model=model_name,
                model_version=model_version,
                analysis_parameters_hash=params_hash
            )
            facts.append(fact)

        # 2. Distill camera motion from motion descriptors
        pan_obs = [o for o in motion_obs if "camera_motion" in o]
        if pan_obs:
            dominant_motion = pan_obs[0]["camera_motion"]
            source_nodes = [o.get("uri") for o in pan_obs if "uri" in o]
            
            fact = CrystallizedFact(
                fact_id=f"fact://clip/{clip_name.replace('.', '_')}/camera_motion",
                type="camera_motion",
                value=dominant_motion,
                confidence=0.85,
                source_nodes=source_nodes,
                source_media_hash=media_hash,
                source_model=model_name,
                model_version=model_version,
                analysis_parameters_hash=params_hash
            )
            facts.append(fact)

        # 3. Consolidate speech topic and usable edit segments
        transcript_obs = [o for o in raw_observations if o.get("type") == "transcript"]
        if transcript_obs:
            full_text = " ".join([o.get("text", "") for o in transcript_obs])
            source_nodes = [o.get("uri") for o in transcript_obs if "uri" in o]
            
            # Simple heuristic speech topic distillation
            topic = "general_vlog"
            if "color" in full_text.lower() or "transition" in full_text.lower():
                topic = "color_grading_and_vfx"
            elif "zoom" in full_text.lower():
                topic = "camera_zoom_effects"
                
            fact_topic = CrystallizedFact(
                fact_id=f"fact://clip/{clip_name.replace('.', '_')}/speech_topic",
                type="speech_topic",
                value=topic,
                confidence=0.88,
                source_nodes=source_nodes,
                source_media_hash=media_hash,
                source_model=model_name,
                model_version=model_version,
                analysis_parameters_hash=params_hash
            )
            facts.append(fact_topic)
            
            # Identify usable high-energy dialog segments
            for i, obs in enumerate(transcript_obs):
                fact_seg = CrystallizedFact(
                    fact_id=f"fact://clip/{clip_name.replace('.', '_')}/usable_segment/{i}",
                    type="usable_segment",
                    value={
                        "start": obs.get("start_seconds"),
                        "end": obs.get("end_seconds"),
                        "score": 0.95 if avg_motion > 0.5 else 0.70
                    },
                    confidence=obs.get("confidence", 0.90),
                    source_nodes=[obs.get("uri")],
                    source_media_hash=media_hash,
                    source_model=model_name,
                    model_version=model_version,
                    analysis_parameters_hash=params_hash
                )
                facts.append(fact_seg)

        # 4. Save distilled facts as Temporal/Semantic nodes inside the MediaGraph
        for fact in facts:
            prov = MediaNodeProvenance(
                created_by="crystallizer_v1",
                confidence=fact.confidence,
                version=model_version
            )
            
            # Map fact to TemporalNode if it contains interval bounds, else SemanticNode
            if isinstance(fact.value, dict) and "start" in fact.value and "end" in fact.value:
                node = TemporalNode(
                    uri=fact.fact_id,
                    provenance=prov,
                    start_seconds=fact.value["start"],
                    end_seconds=fact.value["end"],
                    metadata=fact.model_dump()
                )
            else:
                node = SemanticNode(
                    uri=fact.fact_id,
                    provenance=prov,
                    label=fact.type,
                    score=fact.confidence,
                    metadata=fact.model_dump()
                )
            self.graph_repo.save_node(media_graph_uri, node)
            
        return facts
