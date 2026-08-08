import time
from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository, Entity
from agentforge_core.mediagraph import (
    MediaNodeProvenance,
    TemporalNode,
    SpatialNode,
    SemanticNode,
    MediaGraphRepository
)

def main() -> None:
    print("==================================================")
    print("📊 Running AgentForge Decoupled Media Graph Diagnostics")
    print("==================================================")

    # 1. Setup DI storage repo
    repo = SQLiteGraphRepository(":memory:")
    container = get_container()
    container.register(GraphRepository, repo)
    print("✓ Persistent storage registered in DI Container.")

    graph_repo = MediaGraphRepository()
    
    # 2. Register root video entity
    graph_uri = "graph://video/agentforge-os-teaser"
    repo.save_entity(Entity(uri=graph_uri, type="media_graph"))
    print(f"✓ Created root media graph: {graph_uri}")

    # 3. Add Shot Cuts (TemporalNodes)
    print("\n[Shot Cuts] Adding shot segment nodes...")
    s0_provenance = MediaNodeProvenance(created_by="scene_detector_v1", confidence=0.98)
    shot0 = TemporalNode(
        uri="node://shot/0",
        provenance=s0_provenance,
        start_seconds=0.0,
        end_seconds=3.0,
        metadata={"motion_score": 15.0}
    )
    graph_repo.save_node(graph_uri, shot0)

    s1_provenance = MediaNodeProvenance(created_by="scene_detector_v1", confidence=0.95)
    shot1 = TemporalNode(
        uri="node://shot/1",
        provenance=s1_provenance,
        start_seconds=3.0,
        end_seconds=8.0,
        metadata={"motion_score": 85.0}
    )
    graph_repo.save_node(graph_uri, shot1)
    
    # Add Face recognition spatial node inside shot1
    face_prov = MediaNodeProvenance(created_by="face_tracker_v1", confidence=0.90)
    face0 = SpatialNode(
        uri="node://face/0",
        provenance=face_prov,
        bounding_box=[50.0, 60.0, 120.0, 130.0],
        metadata={"label": "Presenter face"}
    )
    graph_repo.save_node(graph_uri, face0, parent_uri=shot1.uri)
    print("✓ Saved shot and nested face recognition coordinates.")

    # 4. Add Color Palettes (SemanticNodes)
    print("\n[Color Palettes] Adding dominant palette nodes...")
    color_prov = MediaNodeProvenance(created_by="color_analyzer_v1")
    color0 = SemanticNode(
        uri="node://color/nvidia-green",
        provenance=color_prov,
        label="Nvidia Green",
        score=94.0,
        metadata={"hex": "#76B900"}
    )
    graph_repo.save_node(graph_uri, color0)
    print("✓ Saved Nvidia Green semantic node.")

    # 5. Queries and Lineage Verifications
    print("\n[Graph Queries] Resolving full media graph lineage...")
    nodes = graph_repo.get_graph_nodes(graph_uri)
    print(f"✓ Discovered {len(nodes)} related nodes under root:")
    for node in nodes:
        prov_desc = f"[Created by: {node.provenance.created_by} | Conf: {node.provenance.confidence}]"
        
        if isinstance(node, TemporalNode):
            print(f"  ├── Temporal ({node.uri}) range: {node.start_seconds}s ➔ {node.end_seconds}s {prov_desc}")
            # Check for nested sub-nodes
            sub_nodes = repo.get_related_entities(node.uri, "parent_of")
            for sub in sub_nodes:
                print(f"  │   └── nested child spatial node: {sub.uri}")
                
        elif isinstance(node, SpatialNode):
            print(f"  ├── Spatial ({node.uri}) coordinates: {node.bounding_box} {prov_desc}")
            
        elif isinstance(node, SemanticNode):
            print(f"  ├── Semantic ({node.uri}) classification: '{node.label}' (score: {node.score}) {prov_desc}")

    print("==================================================")
    print("🎉 DECOUPLED MEDIA GRAPH DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
