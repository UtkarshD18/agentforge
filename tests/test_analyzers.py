import pytest
from agentforge_analyzers import BaseAnalyzer, AnalyzerRegistry

class MockAnalyzer(BaseAnalyzer):
    def __init__(self, name: str, requires: list, produces: list, priority: int = 10) -> None:
        self.name = name
        self._requires = requires
        self._produces = produces
        self._priority = priority

    @property
    def requires(self) -> list:
        return self._requires

    @property
    def produces(self) -> list:
        return self._produces

    @property
    def priority(self) -> int:
        return self._priority

    def run(self, graph_uri: str, input_path: str) -> None:
        pass

def test_analyzer_dependency_resolution():
    registry = AnalyzerRegistry()

    # Define mock analyzers with dependency chains
    # Shot detector: video -> shots
    shots_det = MockAnalyzer("shots_det", requires=["video"], produces=["shots"], priority=10)
    # Face tracker: shots -> faces
    faces_tr = MockAnalyzer("faces_tr", requires=["shots"], produces=["faces"], priority=5)
    # Subtitle generator: audio -> transcript
    sub_gen = MockAnalyzer("sub_gen", requires=["audio"], produces=["transcript"], priority=10)
    # Hook predictor: transcript -> hook_score
    hook_pred = MockAnalyzer("hook_pred", requires=["transcript"], produces=["hook_score"], priority=5)

    registry.register_analyzer(shots_det)
    registry.register_analyzer(faces_tr)
    registry.register_analyzer(sub_gen)
    registry.register_analyzer(hook_pred)

    # 1. Resolve pipeline for faces analysis
    pipeline_faces = registry.resolve_pipeline(["faces"])
    assert len(pipeline_faces) == 2
    assert pipeline_faces[0].name == "shots_det" # shots must run first
    assert pipeline_faces[1].name == "faces_tr"

    # 2. Resolve pipeline for hook prediction
    pipeline_hook = registry.resolve_pipeline(["hook_score"])
    assert len(pipeline_hook) == 2
    assert pipeline_hook[0].name == "sub_gen" # sub_gen must run first
    assert pipeline_hook[1].name == "hook_pred"

def test_analyzer_cyclic_dependency():
    registry = AnalyzerRegistry()

    # Define cyclical dependencies
    analyzer_a = MockAnalyzer("analyzer_a", requires=["output_b"], produces=["output_a"])
    analyzer_b = MockAnalyzer("analyzer_b", requires=["output_a"], produces=["output_b"])

    registry.register_analyzer(analyzer_a)
    registry.register_analyzer(analyzer_b)

    with pytest.raises(ValueError) as exc_info:
        registry.resolve_pipeline(["output_a"])
    assert "Cyclic dependency detected" in str(exc_info.value)
