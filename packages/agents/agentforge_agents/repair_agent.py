import logging
from typing import Dict, Any, List
from agentforge_agents.director_agent import RichEditPlan, EditPlanSegment

class RepairAgent:
    """
    Decoupled Repair Agent.
    1. Reads TimelineAuditor mismatch results.
    2. Identifies specific mismatches (e.g. durational offsets, missing clips).
    3. Generates a minimal RepairPlan (adjusting EditPlan range inputs).
    4. Capped strictly at a maximum of 3 repair iterations.
    """
    def __init__(self) -> None:
        self.logger = logging.getLogger("agentforge.repair_agent")

    def generate_repair_plan(
        self,
        original_plan: RichEditPlan,
        audit_results: Dict[str, Any],
        iteration: int
    ) -> RichEditPlan:
        if iteration > 3:
            self.logger.error("Max repair cycles (3) exceeded. Aborting repair.")
            return original_plan

        repaired_plan = original_plan.model_copy(deep=True)
        items = audit_results.get("items", [])
        
        # Adjust original segment boundaries to match actual offsets if mismatches occur
        for item in items:
            idx = item.get("index")
            match = item.get("match")
            if not match and idx is not None and idx < len(repaired_plan.operations):
                expected_dur = item.get("scaled_expected_duration") or item.get("expected_duration")
                actual_dur = item.get("actual_duration")
                seg = repaired_plan.operations[idx]
                
                # Adjust end frame to correct duration offsets
                diff = expected_dur - actual_dur
                if diff != 0:
                    seg.source_end = seg.source_end + diff
                    self.logger.info(f"[RepairAgent] Cycle {iteration}: Adjusted segment {idx} source_end by {diff} frames.")
                    
        return repaired_plan
