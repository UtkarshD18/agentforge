from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository, Entity
from agentforge_core.mediagraph import (
    MediaNodeProvenance,
    TemporalNode,
    SemanticNode,
    MediaGraphRepository
)
from agentforge_analyzers import BaseAnalyzer, AnalyzerRegistry

class SceneDetector(BaseAnalyzer):
    @property
    def requires(self) -> list:
        return ["video"]

    @property
    def produces(self) -> list:
        return ["scenes"]

    def run(self, graph_uri: str, input_path: str) -> None:
        print("  - Running SceneDetector...")
        # Save a shot temporal node in graph
        shot = TemporalNode(
            uri="node://shot/0",
            provenance=MediaNodeProvenance(created_by="scene_detector_v1"),
            start_seconds=0.0,
            end_seconds=10.0
        )
        repo = MediaGraphRepository()
        repo.save_node(graph_uri, shot)

class MotionAnalyzer(BaseAnalyzer):
    @property
    def requires(self) -> list:
        return ["scenes"]

    @property
    def produces(self) -> list:
        return ["motion_profile"]

    def run(self, graph_uri: str, input_path: str) -> None:
        print("  - Running MotionAnalyzer...")
        # Fetch shot nodes from the graph
        repo = MediaGraphRepository()
        shots = repo.get_graph_nodes(graph_uri)
        
        # Analyze first shot and save motion semantic node
        if shots:
            parent_shot = shots[0]
            motion = SemanticNode(
                uri="node://motion/0",
                provenance=MediaNodeProvenance(created_by="motion_analyzer_v1"),
                label="High Motion Activity",
                score=82.5
            )
            # Save related to parent shot
            repo.save_node(graph_uri, motion, parent_uri=parent_shot.uri)

def main() -> None:
    print("==================================================")
    print("🚀 Running AgentForge Analyzer Framework Diagnostics")
    print("==================================================")

    # 1. Setup DI storage repo for persistence
    db = SQLiteGraphRepository(":memory:")
    container = get_container()
    container.register(GraphRepository, db)
    print("✓ Storage Repository registered in DI Container.")

    # 2. Setup registry and register analyzers
    registry = AnalyzerRegistry()
    registry.register_analyzer(SceneDetector())
    registry.register_analyzer(MotionAnalyzer())
    print("✓ SceneDetector and MotionAnalyzer registered in registry.")

    # 3. Resolve execution pipeline for 'motion_profile'
    print("\n[DAG Scheduling] Resolving analyzer execution pipeline...")
    pipeline = registry.resolve_pipeline(["motion_profile"])
    print("✓ Scheduled Pipeline execution sequence:")
    for idx, analyzer in enumerate(pipeline):
        print(f"  [{idx}] {analyzer.__class__.__name__} (Requires: {analyzer.requires} ➔ Produces: {analyzer.produces})")

    # 4. Run pipeline
    graph_uri = "graph://video/agentforge-test"
    db.save_entity(Entity(uri=graph_uri, type="media_graph"))
    
    print("\n[Execution Pipeline] Executing scheduled pipeline on graph...")
    for analyzer in pipeline:
        analyzer.run(graph_uri, "/path/to/video.mp4")

    # 5. Verify database nodes and parent relationships
    print("\n[Results Validation] Querying generated media graph nodes...")
    repo = MediaGraphRepository()
    nodes = repo.get_graph_nodes(graph_uri)
    print(f"✓ Discovered {len(nodes)} related nodes under root:")
    for node in nodes:
        prov_desc = f"[Created by: {node.provenance.created_by}]"
        
        if isinstance(node, TemporalNode):
            print(f"  ├── Temporal ({node.uri}) range: {node.start_seconds}s ➔ {node.end_seconds}s {prov_desc}")
            # Check for nested sub-nodes
            sub_nodes = db.get_related_entities(node.uri, "parent_of")
            for sub in sub_nodes:
                print(f"  │   └── nested child node: {sub.uri}")
                
        elif isinstance(node, SemanticNode):
            print(f"  ├── Semantic ({node.uri}) label: '{node.label}' (score: {node.score}) {prov_desc}")

    print("==================================================")
    print("🎉 ANALYZER FRAMEWORK DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
