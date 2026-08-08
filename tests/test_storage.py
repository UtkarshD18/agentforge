import pytest
from agentforge_core.storage import (
    Entity,
    SQLiteGraphRepository,
    SQLiteEventRepository,
    SQLiteArtifactRepository,
    LocalFileSystemBlobRepository,
    SQLiteSettingsRepository,
    SurrealDBGraphRepository
)
from agentforge_core.artifacts import ArtifactManager
import tempfile
import os

def test_entity_lifecycle():
    repo = SQLiteGraphRepository(":memory:")
    
    entity = Entity(uri="workspace://w1", type="workspace", metadata={"name": "My Workspace"})
    repo.save_entity(entity)
    
    retrieved = repo.get_entity("workspace://w1")
    assert retrieved is not None
    assert retrieved.uri == "workspace://w1"
    assert retrieved.type == "workspace"
    assert retrieved.metadata == {"name": "My Workspace"}
    
    # Update entity
    entity.metadata["name"] = "Updated Workspace"
    repo.save_entity(entity)
    retrieved = repo.get_entity("workspace://w1")
    assert retrieved.metadata == {"name": "Updated Workspace"}
    
    # Delete entity
    repo.delete_entity("workspace://w1")
    assert repo.get_entity("workspace://w1") is None

def test_entity_relationships():
    repo = SQLiteGraphRepository(":memory:")
    
    agent = Entity(uri="agent://a1", type="agent", metadata={"name": "Editor"})
    task = Entity(uri="task://t1", type="task", metadata={"instruction": "Trim silence"})
    
    repo.save_entity(agent)
    repo.save_entity(task)
    
    # Relate agent -[owns]-> task
    repo.relate_entities("agent://a1", "task://t1", "owns")
    
    related = repo.get_related_entities("agent://a1", "owns")
    assert len(related) == 1
    assert related[0].uri == "task://t1"
    
    # Cascade delete verification: deleting agent should delete the relation edge
    repo.delete_entity("agent://a1")
    
    # Clean verification
    related_after = repo.get_related_entities("agent://a1", "owns")
    assert len(related_after) == 0

def test_event_sourcing_logs():
    repo = SQLiteEventRepository(":memory:")
    
    correlation_id = "c-12345"
    repo.log_event("task.started", correlation_id, {"task_uri": "task://t1"})
    repo.log_event("task.completed", correlation_id, {"task_uri": "task://t1", "status": "ok"})
    
    logs = repo.get_event_logs(correlation_id)
    assert len(logs) == 2
    assert logs[0]["event_type"] == "task.started"
    assert logs[0]["payload"] == {"task_uri": "task://t1"}
    assert logs[1]["event_type"] == "task.completed"
    assert logs[1]["payload"] == {"task_uri": "task://t1", "status": "ok"}

def test_surrealdb_lifecycle():
    # 1. Initialize SurrealDB Repository
    repo = SurrealDBGraphRepository(url="http://localhost:8000")
    
    # 2. Skip test if SurrealDB is not running locally to prevent CI failure
    try:
        # Check connection by deleting a dummy URI
        repo.delete_entity("test://connectivity")
    except (ConnectionError, ValueError):
        pytest.skip("SurrealDB is not running on http://localhost:8000. Skipping SurrealDB integration test.")

    # 3. If connected, perform full integration lifecycle check
    uri = "test://node/1"
    entity = Entity(uri=uri, type="test_node", metadata={"status": "active"})
    repo.save_entity(entity)
    
    retrieved = repo.get_entity(uri)
    assert retrieved is not None
    assert retrieved.uri == uri
    assert retrieved.metadata == {"status": "active"}
    
    # Relate
    target_uri = "test://node/2"
    repo.save_entity(Entity(uri=target_uri, type="target_node"))
    repo.relate_entities(uri, target_uri, "links_to")
    
    related = repo.get_related_entities(uri, "links_to")
    assert len(related) == 1
    assert related[0].uri == target_uri
    
    # Cleanup
    repo.delete_entity(uri)
    repo.delete_entity(target_uri)

def test_artifact_manager_and_repos():
    # 1. Setup repos
    artifact_repo = SQLiteArtifactRepository(":memory:")
    with tempfile.TemporaryDirectory() as tmp_blob_dir:
        blob_repo = LocalFileSystemBlobRepository(tmp_blob_dir)
        manager = ArtifactManager(artifact_repo, blob_repo)

        # 2. Create dummy file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"Hello AgentForge Execution Fabric")
            dummy_file_path = f.name

        try:
            # 3. Register file
            meta = manager.register_file(
                file_path=dummy_file_path,
                mime_type="text/plain",
                creator="test_runner",
                metadata={"workflow": "diagnostics"}
            )

            # 4. Verify metadata
            assert meta.uri.startswith("artifact://")
            assert meta.mime_type == "text/plain"
            assert meta.creator == "test_runner"
            assert meta.metadata == {"workflow": "diagnostics"}

            # 5. Query back
            retrieved = manager.get_artifact(meta.uri)
            assert retrieved is not None
            assert retrieved.checksum == meta.checksum

            # 6. Retrieve local path and check contents
            local_path = manager.get_local_path(meta.uri)
            assert local_path is not None
            assert os.path.exists(local_path)
            with open(local_path, "rb") as bf:
                assert bf.read() == b"Hello AgentForge Execution Fabric"

            # 7. Test lineage derivation
            with tempfile.NamedTemporaryFile(delete=False) as child_f:
                child_f.write(b"Derived child content")
                child_file_path = child_f.name

            try:
                child_meta = manager.register_file(
                    file_path=child_file_path,
                    mime_type="text/plain",
                    creator="derived_transcoder",
                    parent_artifact_uri=meta.uri
                )
                assert child_meta.parent_artifact_uri == meta.uri

                retrieved_child = manager.get_artifact(child_meta.uri)
                assert retrieved_child is not None
                assert retrieved_child.parent_artifact_uri == meta.uri
            finally:
                if os.path.exists(child_file_path):
                    os.remove(child_file_path)

        finally:
            if os.path.exists(dummy_file_path):
                os.remove(dummy_file_path)

def test_settings_repository():
    settings_repo = SQLiteSettingsRepository(":memory:")
    settings_repo.set_setting("theme", "dark")
    settings_repo.set_setting("workers_count", 4)

    assert settings_repo.get_setting("theme") == "dark"
    assert settings_repo.get_setting("workers_count") == 4
    assert settings_repo.get_setting("non_existent") is None
