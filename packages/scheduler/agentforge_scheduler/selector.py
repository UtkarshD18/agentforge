from typing import List, Dict, Any, Optional

class WorkerSelector:
    def filter_workers(self, requirements: Dict[str, Any], workers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        required_labels = requirements.get("labels", [])
        matched = []
        for w in workers:
            labels = w.get("profile", {}).get("labels", [])
            if all(lbl in labels for lbl in required_labels):
                matched.append(w)
        return matched

class ProviderSelector:
    def select_best_provider(self, capability: str, registrations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not registrations:
            return None
        sorted_regs = sorted(registrations, key=lambda r: r.get("score", 0.0), reverse=True)
        return sorted_regs[0]
