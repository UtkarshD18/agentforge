import os
import pytest
from agentforge_core.storage import SQLiteGraphRepository, GraphRepository, Entity
from agentforge_core.di import get_container
from agentforge_core.mediagraph import MediaGraphRepository, TemporalNode
from agentforge_resources import ResourceManager, ModelManager
from agentforge_agents import AudioTranscriptionAgent

def test_audio_agent_transcription_and_graph_write():
    # 1. Setup in-memory SQLite DB and register it in DI container
    container = get_container()
    container.clear()
    
    db_repo = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, db_repo)
    
    # 2. Instantiate systems
    resources = ResourceManager(safety_ceiling_bytes=6 * 1024 * 1024 * 1024)
    model_mgr = ModelManager(resources)
    graph_repo = MediaGraphRepository(db_repo)
    
    agent = AudioTranscriptionAgent(
        resource_manager=resources,
        model_manager=model_mgr,
        graph_repo=graph_repo
    )
    
    # Check VRAM is clear before execution
    assert resources.allocated_vram_bytes == 0
    
    # 3. Trigger transcription on a sample clip
    # We point to the actual video file on the machine
    clip_path = "/home/shadow/Videos/DaVinci/clips/IMG_0208.mov"
    media_graph_uri = "db://media-graph-test"
    
    # Save the root mediagraph node to prevent foreign key errors
    db_repo.save_entity(Entity(uri=media_graph_uri, type="mediagraph"))
    
    success = agent.transcribe_clip("IMG_0208.mov", clip_path, media_graph_uri)
    assert success is True
    
    # 4. Verify model is completely unloaded from VRAM
    assert resources.allocated_vram_bytes == 0
    assert len(resources.active_allocations) == 0
    
    # 5. Query MediaGraph and verify transcript nodes were saved
    nodes = graph_repo.get_graph_nodes(media_graph_uri)
    assert len(nodes) > 0
    
    transcript_nodes = [n for n in nodes if "transcript" in n.uri]
    assert len(transcript_nodes) > 0
    
    # Verify metadata fields exist and text is retrieved
    first_node = transcript_nodes[0]
    assert isinstance(first_node, TemporalNode)
    assert first_node.metadata["clip_name"] == "IMG_0208.mov"
    assert len(first_node.metadata["text"]) > 0
    assert first_node.provenance.created_by == "whisper_agent_v1"
