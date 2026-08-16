import os
import pytest
from typing import List

from agentforge_core.storage import SQLiteGraphRepository, GraphRepository, SQLiteTelemetryRepository, TelemetryRepository, Entity
from agentforge_core.di import get_container
from agentforge_core.mediagraph import MediaGraphRepository, ContextBudgeter, MediaAnalysisCache, TemporalNode, SemanticNode, GraphBuilder
from agentforge_core.events import get_event_bus
from agentforge_resources import ResourceManager, ModelManager, StrategySelector, InferenceStrategy, ModelCapabilityProfile
from agentforge_orchestrator import HierarchicalAnalyzer

def test_strategy_selector_cost_scoring():
    # Setup capability profiles
    profiles = [
        ModelCapabilityProfile(
            model_name="qwen-vl-8b",
            min_vram_bytes=6 * 1024 * 1024 * 1024, # 6 GB base VRAM
            quantization_options=["4bit", "8bit"],
            cpu_offload_support=True,
            layer_streaming_support=True,
            capabilities=["vision"],
            expected_quality=0.88
        ),
        ModelCapabilityProfile(
            model_name="gemini-2.5-flash",
            min_vram_bytes=0, # Remote Cloud
            local=False,
            capabilities=["vision"],
            expected_quality=0.95
        )
    ]
    
    selector = StrategySelector(profiles)
    
    # Scenario A: Ample VRAM (e.g. 8 GB free), local quantized/full GPU should be preferred
    best = selector.select_best_strategy(
        required_capabilities=["vision"],
        live_free_vram=8 * 1024 * 1024 * 1024,
        live_free_ram=16 * 1024 * 1024 * 1024,
        latency_weight=1.0,
        quality_weight=1.0,
        memory_weight=0.1, # low memory penalty to prioritize local GPU
        cost_weight=2.0    # high cost penalty to avoid Cloud
    )
    assert best is not None
    assert best[0].model_name == "qwen-vl-8b"
    assert best[1] in [InferenceStrategy.FULL_GPU, InferenceStrategy.QUANTIZED]

    # Scenario B: Low VRAM (e.g. 1 GB free), standard full GPU won't fit. Pick layer streaming or cloud.
    # If latency weight is high, avoid layer streaming overhead and select Cloud.
    best_low = selector.select_best_strategy(
        required_capabilities=["vision"],
        live_free_vram=1 * 1024 * 1024 * 1024,
        live_free_ram=16 * 1024 * 1024 * 1024,
        latency_weight=3.0, # high latency sensitivity
        quality_weight=1.0,
        memory_weight=1.0,
        cost_weight=0.1
    )
    assert best_low is not None
    assert best_low[1] == InferenceStrategy.CLOUD

    # Scenario C: Tight VRAM (600 MB free) but low latency sensitivity (long batch process). Pick layer streaming.
    best_streaming = selector.select_best_strategy(
        required_capabilities=["vision"],
        live_free_vram=600 * 1024 * 1024, # 600 MB
        live_free_ram=16 * 1024 * 1024 * 1024,
        latency_weight=0.1, # low latency sensitivity
        quality_weight=1.0,
        memory_weight=1.0,
        cost_weight=4.0 # high monetary cost penalty (avoid cloud)
    )
    assert best_streaming is not None
    assert best_streaming[0].model_name == "qwen-vl-8b"
    assert best_streaming[1] == InferenceStrategy.LAYER_STREAMING

def test_knowledge_crystallizer_provenance():
    container = get_container()
    container.clear()
    db = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, db)
    graph_repo = MediaGraphRepository(db)
    
    # Save root node
    graph_uri = "db://media"
    db.save_entity(Entity(uri=graph_uri, type="mediagraph"))
    
    from agentforge_orchestrator.crystallizer import KnowledgeCrystallizer
    crystallizer = KnowledgeCrystallizer(graph_repo)
    
    # Populate raw observations
    raw_obs = [
        {"type": "motion", "energy": 0.92, "camera_motion": "pan_left", "uri": "node://obs/motion/1"},
        {"type": "transcript", "start_seconds": 1.0, "end_seconds": 3.0, "text": "Zoom effects tutorial", "confidence": 0.95, "uri": "node://obs/transcript/1"}
    ]
    
    facts = crystallizer.crystallize_and_save(
        media_graph_uri=graph_uri,
        clip_name="IMG_0208.mov",
        media_hash="abc123sha",
        raw_observations=raw_obs,
        model_name="qwen-vl-8b",
        model_version="1.0",
        params={"res": "1080p"}
    )
    
    assert len(facts) > 0
    # Verify provenance lists
    energy_fact = [f for f in facts if f.type == "visual_energy"][0]
    assert "node://obs/motion/1" in energy_fact.source_nodes
    assert energy_fact.source_media_hash == "abc123sha"
    assert energy_fact.source_model == "qwen-vl-8b"
    
    topic_fact = [f for f in facts if f.type == "speech_topic"][0]
    assert "node://obs/transcript/1" in topic_fact.source_nodes
    assert topic_fact.value == "camera_zoom_effects"

def test_context_budgeter_modality_limits():
    # Setup test nodes with varying confidence scores
    nodes = [
        GraphBuilder.build_color_node("palette_1", "High confidence fact", 0.95, "creator_1"),
        GraphBuilder.build_color_node("palette_2", "Low confidence fact", 0.40, "creator_1"),
        GraphBuilder.build_color_node("palette_3", "Medium confidence fact", 0.75, "creator_1")
    ]
    
    # Token budget set tight (20 tokens)
    budgeter = ContextBudgeter(text_token_limit=20)
    result = budgeter.compile_budgeted_context(nodes)
    
    # Confirm highest confidence node is preserved while budget bounds are respected
    assert "palette_1" in result["text"]
    assert "palette_2" not in result["text"] # Evicted first due to low ranking
    assert result["tokens_used"] <= 20

def test_media_analysis_cache_tiers():
    container = get_container()
    container.clear()
    db = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, db)
    graph_repo = MediaGraphRepository(db)
    
    cache_mgr = MediaAnalysisCache(graph_repo)
    
    # In-memory graph uri
    graph_uri = "db://media"
    db.save_entity(Entity(uri=graph_uri, type="mediagraph"))
    
    # 1. Build cache key
    key1 = cache_mgr.build_cache_key("sha256_hash", "vision", "qwen-vl", "1.0", {"param1": 12}, "1.0")
    
    # Verify lookup miss
    assert cache_mgr.get_cached_result(key1) is None
    
    # 2. Save cached analysis result
    mock_result = {"labels": ["street", "car"]}
    cache_mgr.save_cached_result(graph_uri, key1, "L2", mock_result)
    
    # Verify lookup hit
    assert cache_mgr.get_cached_result(key1) == mock_result
    
    # 3. Check invalidation if params or analyzer version change
    key2 = cache_mgr.build_cache_key("sha256_hash", "vision", "qwen-vl", "1.0", {"param1": 12}, "1.1") # analyzer version changed
    assert key2 != key1
    assert cache_mgr.get_cached_result(key2) is None

def test_hierarchical_analyzer_e2e():
    container = get_container()
    container.clear()
    db = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, db)
    graph_repo = MediaGraphRepository(db)
    
    telemetry_db = SQLiteTelemetryRepository(":memory:")
    
    # Register graph and telemetry roots
    graph_uri = "db://media"
    db.save_entity(Entity(uri=graph_uri, type="mediagraph"))
    
    profiles = [
        ModelCapabilityProfile(
            model_name="qwen-vl-8b",
            min_vram_bytes=2 * 1024 * 1024 * 1024,
            capabilities=["vision"],
            expected_quality=0.88
        )
    ]
    
    resources = ResourceManager(safety_ceiling_bytes=6 * 1024 * 1024 * 1024)
    model_mgr = ModelManager(resources)
    
    analyzer = HierarchicalAnalyzer(
        resource_manager=resources,
        model_manager=model_mgr,
        graph_repo=graph_repo,
        telemetry_repo=telemetry_db,
        profiles=profiles
    )
    
    events_dispatched = []
    def log_event(event):
        events_dispatched.append(event.event_type)
        
    bus = get_event_bus()
    bus.subscribe(log_event)
    
    # Run analysis
    success = analyzer.run_multimodal_analysis("IMG_0208.mov", "/home/shadow/Videos/DaVinci/clips/IMG_0208.mov", graph_uri)
    assert success is True
    
    # 1. Assert Event Dispatch steps
    assert "ClipDiscovered" in events_dispatched
    assert "CheapAnalysisCompleted" in events_dispatched
    assert "CandidateSegmentsReady" in events_dispatched
    assert "VisionAnalysisCompleted" in events_dispatched
    assert "KnowledgeCrystallized" in events_dispatched
    
    # 2. Verify Telemetry Logging was saved in sqlite
    logs = telemetry_db.get_telemetry("qwen-vl-8b")
    assert len(logs) > 0
    assert logs[0]["strategy"] == InferenceStrategy.FULL_GPU.value
    assert logs[0]["success"] == 1
    assert logs[0]["quality_score"] == 0.92
