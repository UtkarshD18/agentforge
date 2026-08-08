import pytest
from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository, Entity
from agentforge_core.mediagraph import (
    MediaNodeProvenance,
    TemporalNode,
    SpatialNode,
    SemanticNode,
    MediaGraphRepository,
    GraphBuilder
)

def test_decoupled_mediagraph_nodes():
    container = get_container()
    container.clear()
    
    # 1. Setup DI storage repo
    repo = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, repo)
    
    graph_repo = MediaGraphRepository()
    
    # Define root video entity
    graph_uri = "graph://video/teaser"
    repo.save_entity(Entity(uri=graph_uri, type="media_graph"))
    
    # 2. Add Shot segment node (Temporal)
    shot_provenance = MediaNodeProvenance(created_by="scene_detector_v1", confidence=0.98)
    shot_node = TemporalNode(
        uri="node://shot/1",
        provenance=shot_provenance,
        start_seconds=0.0,
        end_seconds=4.5,
        metadata={"codec": "h264"}
    )
    graph_repo.save_node(graph_uri, shot_node)
    
    # 3. Add Face node (Spatial) nested inside the Shot
    face_provenance = MediaNodeProvenance(created_by="face_tracker_v1", confidence=0.85)
    face_node = SpatialNode(
        uri="node://face/1",
        provenance=face_provenance,
        bounding_box=[10.0, 20.0, 150.0, 200.0]
    )
    graph_repo.save_node(graph_uri, face_node, parent_uri=shot_node.uri)
    
    # 4. Add Color palette node (Semantic)
    color_provenance = MediaNodeProvenance(created_by="color_analyzer_v1")
    color_node = SemanticNode(
        uri="node://colors/1",
        provenance=color_provenance,
        label="Nvidia Green",
        score=92.0,
        metadata={"hex": "#76B900"}
    )
    graph_repo.save_node(graph_uri, color_node)
    
    # 5. Queries and Assertions
    # Fetch all nodes related to the graph root
    graph_nodes = graph_repo.get_graph_nodes(graph_uri)
    assert len(graph_nodes) == 3 # shot, face, colors
    
    # Fetch specific node
    loaded_shot = graph_repo.get_node("node://shot/1")
    assert isinstance(loaded_shot, TemporalNode)
    assert loaded_shot.start_seconds == 0.0
    assert loaded_shot.end_seconds == 4.5
    assert loaded_shot.provenance.created_by == "scene_detector_v1"
    
    # Verify nested relationship
    nested = repo.get_related_entities(shot_node.uri, "parent_of")
    assert len(nested) == 1
    assert nested[0].uri == face_node.uri

def test_graph_builder():
    # 1. Build shot node
    shot = GraphBuilder.build_shot_node(
        index=3,
        start_seconds=12.5,
        end_seconds=15.0,
        creator="test_scene_detector",
        confidence=0.92,
        metadata={"keyframe": "/tmp/k3.jpg"}
    )
    assert isinstance(shot, TemporalNode)
    assert shot.uri == "node://shot/3?rev=1"
    assert shot.start_seconds == 12.5
    assert shot.end_seconds == 15.0
    assert shot.provenance.created_by == "test_scene_detector"
    assert shot.provenance.confidence == 0.92
    assert shot.metadata == {"keyframe": "/tmp/k3.jpg"}

    # 2. Build face node
    face = GraphBuilder.build_face_node(
        index=8,
        bounding_box=[10, 20, 100, 120],
        creator="test_face_tracker",
        confidence=0.88
    )
    assert isinstance(face, SpatialNode)
    assert face.uri == "node://face/8?rev=1"
    assert face.bounding_box == [10, 20, 100, 120]
    assert face.provenance.created_by == "test_face_tracker"

    # 3. Build color node
    color = GraphBuilder.build_color_node(
        palette_id="green",
        label="Nvidia Green",
        score=99.0,
        creator="test_color_analyzer"
    )
    assert isinstance(color, SemanticNode)
    assert color.uri == "node://colors/green?rev=1"
    assert color.label == "Nvidia Green"
    assert color.score == 99.0
    assert color.provenance.created_by == "test_color_analyzer"
