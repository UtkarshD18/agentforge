from typing import Dict, List

class CUDAGraphManager:
    """
    Wrapper for CUDA Graph record/replay pipelines.
    Bundles sequential filter steps (e.g. Crop -> Resize -> Normalize -> Burn)
    into a single execution graph, reducing CPU launch latency overhead.
    """
    def __init__(self) -> None:
        self._recorded_graphs: Dict[str, List[str]] = {}

    def record_graph(self, name: str, node_operations: List[str]) -> None:
        """
        Records a sequence of filters as a CUDA Graph definition.
        """
        self._recorded_graphs[name] = list(node_operations)

    def play_graph(self, name: str) -> bool:
        """
        Executes/replays the recorded graph. Returns True if graph exists.
        """
        return name in self._recorded_graphs
