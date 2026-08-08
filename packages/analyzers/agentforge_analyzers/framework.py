from abc import ABC, abstractmethod
from typing import List, Dict, Set, Optional

class BaseAnalyzer(ABC):
    """
    Abstract Base Class for pluggable media analyzers.
    """
    @property
    @abstractmethod
    def requires(self) -> List[str]:
        """
        List of data dependencies required before this analyzer can execute (e.g. ['transcript']).
        """
        pass

    @property
    @abstractmethod
    def produces(self) -> List[str]:
        """
        List of nodes this analyzer writes to the Media Graph (e.g. ['hook_score']).
        """
        pass

    @property
    def priority(self) -> int:
        """
        Execution priority tier (higher priority executes first).
        """
        return 10

    @abstractmethod
    def run(self, graph_uri: str, input_path: str) -> None:
        """
        Executes analysis logic and saves nodes in the MediaGraphRepository.
        """
        pass

class AnalyzerRegistry:
    """
    Thread-safe registry for discovery and topological DAG pipeline scheduling
    of pluggable media analyzers.
    """
    def __init__(self) -> None:
        self._analyzers: List[BaseAnalyzer] = []
        import threading
        self._lock = threading.Lock()

    def register_analyzer(self, analyzer: BaseAnalyzer) -> None:
        with self._lock:
            self._analyzers.append(analyzer)

    def resolve_pipeline(self, target_capabilities: List[str]) -> List[BaseAnalyzer]:
        """
        Builds a dependency-ordered list of analyzers to execute
        to fulfill the target capabilities.
        Uses a standard topological sort algorithm.
        """
        with self._lock:
            # 1. Build a pool of all candidates contributing to target capabilities
            # and trace back their requirements recursively.
            selected: Set[BaseAnalyzer] = set()
            
            def collect_dependencies(caps: List[str]):
                for cap in caps:
                    # Find analyzers producing this capability
                    for analyzer in self._analyzers:
                        if cap in analyzer.produces and analyzer not in selected:
                            selected.add(analyzer)
                            # Recursively collect dependencies of this analyzer
                            collect_dependencies(analyzer.requires)

            collect_dependencies(target_capabilities)
            
            # 2. Perform Topological Sort on selected candidates
            ordered_pipeline: List[BaseAnalyzer] = []
            visited: Set[BaseAnalyzer] = set()
            temp_marked: Set[BaseAnalyzer] = set()

            def visit(node: BaseAnalyzer):
                if node in temp_marked:
                    raise ValueError("Cyclic dependency detected in analyzer pipeline.")
                if node not in visited:
                    temp_marked.add(node)
                    # Visit dependencies first
                    for req in node.requires:
                        # Find analyzers in our selected set that produce this requirement
                        for dep_node in selected:
                            if req in dep_node.produces:
                                visit(dep_node)
                    temp_marked.remove(node)
                    visited.add(node)
                    ordered_pipeline.append(node)

            for node in sorted(selected, key=lambda x: x.priority, reverse=True):
                if node not in visited:
                    visit(node)

            return ordered_pipeline
