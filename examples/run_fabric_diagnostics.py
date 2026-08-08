import os
import tempfile
from agentforge_core.di import get_container
from agentforge_core.storage import (
    GraphRepository,
    EventRepository,
    ArtifactRepository,
    BlobRepository,
    SettingsRepository,
    VectorRepository,
    SQLiteGraphRepository,
    SQLiteEventRepository,
    SQLiteArtifactRepository,
    LocalFileSystemBlobRepository,
    SQLiteSettingsRepository,
    InMemoryVectorRepository,
    Entity
)
from agentforge_core.mediagraph import MediaGraphRepository, GraphBuilder
from agentforge_core.artifacts import ArtifactManager

def main() -> None:
    print("==================================================")
    print("🚀 Running AgentForge Persistence Layer Diagnostics")
    print("==================================================")

    # 1. Setup DI container and register all 5 repositories
    container = get_container()
    container.clear()

    graph_repo = SQLiteGraphRepository(":memory:")
    event_repo = SQLiteEventRepository(":memory:")
    artifact_repo = SQLiteArtifactRepository(":memory:")
    settings_repo = SQLiteSettingsRepository(":memory:")
    vector_repo = InMemoryVectorRepository()

    # Use a temporary directory for local file blob transfers
    with tempfile.TemporaryDirectory() as tmp_blob_dir:
        blob_repo = LocalFileSystemBlobRepository(tmp_blob_dir)

        container.register(GraphRepository, graph_repo)
        container.register(EventRepository, event_repo)
        container.register(ArtifactRepository, artifact_repo)
        container.register(BlobRepository, blob_repo)
        container.register(SettingsRepository, settings_repo)
        container.register(VectorRepository, vector_repo)
        print("✓ All 6 Persistence Layer Repositories registered in DI Container.")

        # 2. Instantiate managers
        manager = ArtifactManager()
        graph_manager = MediaGraphRepository()

        # 3. Create dummy files representing source and derived files
        with tempfile.NamedTemporaryFile(delete=False) as f_source:
            f_source.write(b"raw camera video output bytes")
            source_path = f_source.name

        with tempfile.NamedTemporaryFile(delete=False) as f_derived:
            f_derived.write(b"transcoded video 1080p mp4 bytes")
            derived_path = f_derived.name

        try:
            print("\n[Lineage Plan] Registering source video and transcoded output...")
            # Register parent source video
            meta_source = manager.register_file(
                file_path=source_path,
                mime_type="video/quicktime",
                creator="camera_op"
            )
            print(f"✓ Source Video Artifact registered: {meta_source.uri}")

            # Register child derived video (pointing to parent source)
            meta_derived = manager.register_file(
                file_path=derived_path,
                mime_type="video/mp4",
                creator="transcoder_plugin_v1",
                parent_artifact_uri=meta_source.uri,
                metadata={"codec": "h264_nvenc"}
            )
            print(f"✓ Transcoded Output Artifact registered: {meta_derived.uri}")
            print(f"  └── Derived from Parent Artifact: {meta_derived.parent_artifact_uri}")

            # 4. Use GraphBuilder to construct shot revisions (V1 & V2)
            print("\n[Graph Plan] Building media graph shot nodes for Revisions 1 & 2...")
            
            # Revision 1 shot
            shot_rev1 = GraphBuilder.build_shot_node(
                index=0,
                start_seconds=0.0,
                end_seconds=4.5,
                creator="scene_detector_v1",
                revision=1,
                metadata={"keyframe": "artifact://rev1-frame"}
            )

            # Revision 2 shot (refining boundaries)
            shot_rev2 = GraphBuilder.build_shot_node(
                index=0,
                start_seconds=0.0,
                end_seconds=4.2,
                creator="scene_detector_v2",
                revision=2,
                metadata={"keyframe": "artifact://rev2-frame"}
            )

            # Save both in graph
            graph_uri = "graph://video/teaser"
            graph_repo.save_entity(Entity(uri=graph_uri, type="media_graph"))
            graph_manager.save_node(graph_uri, shot_rev1)
            graph_manager.save_node(graph_uri, shot_rev2)
            
            print(f"✓ Revision 1 Node Saved: {shot_rev1.uri} (Boundary: 0.0s - {shot_rev1.end_seconds}s)")
            print(f"✓ Revision 2 Node Saved: {shot_rev2.uri} (Boundary: 0.0s - {shot_rev2.end_seconds}s)")

            # Query back both revisions from graph
            print("\n[Lineage Validation] Querying nodes under root graph:")
            nodes = graph_manager.get_graph_nodes(graph_uri)
            for node in nodes:
                print(f"  ├── URI: {node.uri}")
                print(f"  │   └── Provenance Revision: {node.provenance.revision} (Created by: {node.provenance.created_by})")

        finally:
            for p in [source_path, derived_path]:
                if os.path.exists(p):
                    os.remove(p)

    print("==================================================")
    print("🎉 PERSISTENCE LAYER DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
