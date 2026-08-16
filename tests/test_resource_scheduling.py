import pytest
from agentforge_resources.manager import ResourceManager
from agentforge_resources.models import ModelManager, ModelLifecycleState
from agentforge_resources.planner import MemoryPlanner, ResourceAcquisitionError

def test_resource_manager_safety_ceiling():
    # Setup safety ceiling at 5 GB, headroom at 1 GB
    resources = ResourceManager(safety_ceiling_bytes=5 * 1024 * 1024 * 1024)
    assert resources.safety_ceiling_bytes == 5 * 1024 * 1024 * 1024
    
    # Try reserving model that fits
    assert resources.reserve("whisper", 2 * 1024 * 1024 * 1024) is True
    assert resources.allocated_vram_bytes == 2 * 1024 * 1024 * 1024
    
    # Try reserving another model that fits
    assert resources.reserve("ocr", 1 * 1024 * 1024 * 1024) is True
    assert resources.allocated_vram_bytes == 3 * 1024 * 1024 * 1024
    
    # Try reserving model that exceeds safety ceiling
    assert resources.reserve("heavy_model", 3 * 1024 * 1024 * 1024) is False
    assert resources.allocated_vram_bytes == 3 * 1024 * 1024 * 1024
    
    # Release model
    resources.release("whisper")
    assert resources.allocated_vram_bytes == 1 * 1024 * 1024 * 1024
    assert "whisper" not in resources.active_allocations

def test_model_manager_lru_eviction():
    resources = ResourceManager(safety_ceiling_bytes=6 * 1024 * 1024 * 1024)
    model_mgr = ModelManager(resources)
    
    # Load Whisper (2 GB)
    assert model_mgr.load_model("whisper", 2 * 1024 * 1024 * 1024) is True
    assert model_mgr.loaded_order == ["whisper"]
    assert model_mgr.active_models["whisper"] == ModelLifecycleState.LOADED
    
    # Load OCR (2 GB)
    assert model_mgr.load_model("ocr", 2 * 1024 * 1024 * 1024) is True
    assert model_mgr.loaded_order == ["whisper", "ocr"]
    
    # Load Vision (2 GB) - Total 6 GB fits exactly
    assert model_mgr.load_model("vision", 2 * 1024 * 1024 * 1024) is True
    assert model_mgr.loaded_order == ["whisper", "ocr", "vision"]
    
    # Access Whisper to move it to MRU (most recently used)
    assert model_mgr.load_model("whisper", 2 * 1024 * 1024 * 1024) is True
    assert model_mgr.loaded_order == ["ocr", "vision", "whisper"]
    
    # Load heavy model (3 GB) -> Requires evicting models until free space >= 3 GB
    # safety_ceiling=6 GB. Current allocated: 6 GB. Free: 0 GB.
    # Eviction candidates from LRU order: "ocr" (2 GB) -> allocated becomes 4 GB. Still doesn't fit.
    # Next candidate: "vision" (2 GB) -> allocated becomes 2 GB. 3 GB fits!
    # Whisper (2 GB) was MRU so it remains loaded!
    assert model_mgr.load_model("heavy_model", 3 * 1024 * 1024 * 1024) is True
    assert model_mgr.active_models["ocr"] == ModelLifecycleState.EVICTED
    assert model_mgr.active_models["vision"] == ModelLifecycleState.EVICTED
    assert model_mgr.active_models["whisper"] == ModelLifecycleState.LOADED
    assert model_mgr.active_models["heavy_model"] == ModelLifecycleState.LOADED
    assert model_mgr.loaded_order == ["whisper", "heavy_model"]

def test_model_manager_pinning_prevents_eviction():
    resources = ResourceManager(safety_ceiling_bytes=5 * 1024 * 1024 * 1024)
    model_mgr = ModelManager(resources)
    
    # Load Model A (2 GB) and Pin it
    assert model_mgr.load_model("model_a", 2 * 1024 * 1024 * 1024) is True
    model_mgr.pin_model("model_a")
    assert model_mgr.active_models["model_a"] == ModelLifecycleState.PINNED
    
    # Load Model B (2 GB) - Not Pinned
    assert model_mgr.load_model("model_b", 2 * 1024 * 1024 * 1024) is True
    
    # Load Model C (2 GB) -> Exceeds safety ceiling (Total needed: 6 GB, ceiling: 5 GB)
    # LRU order: ["model_a", "model_b"]
    # It tries to evict "model_a" but it is PINNED, so it skips it.
    # It evicts "model_b" (2 GB) -> total allocated becomes 2 GB. Model C (2 GB) can fit!
    assert model_mgr.load_model("model_c", 2 * 1024 * 1024 * 1024) is True
    assert model_mgr.active_models["model_a"] == ModelLifecycleState.PINNED
    assert model_mgr.active_models["model_b"] == ModelLifecycleState.EVICTED
    assert model_mgr.active_models["model_c"] == ModelLifecycleState.LOADED
    
    # Unpin Model A and try loading Model D (2.5 GB) -> Must fail since A (2 GB) + C (2 GB) + D (2.5 GB) > 5 GB
    # Candidates: A (2 GB) and C (2 GB). Both are LOADED.
    # LRU order: ["model_a", "model_c"]
    # Evicts A -> allocated=2 GB. D (2.5 GB) still doesn't fit (needs 4.5 GB > 5 GB).
    # Evicts C -> allocated=0 GB. D fits!
    model_mgr.unpin_model("model_a")
    assert model_mgr.load_model("model_d", 3500 * 1024 * 1024) is True
    assert model_mgr.active_models["model_a"] == ModelLifecycleState.EVICTED
    assert model_mgr.active_models["model_c"] == ModelLifecycleState.EVICTED
    assert model_mgr.active_models["model_d"] == ModelLifecycleState.LOADED

def test_memory_planner_context_manager():
    resources = ResourceManager(safety_ceiling_bytes=4 * 1024 * 1024 * 1024)
    model_mgr = ModelManager(resources)
    planner = MemoryPlanner(resources, model_mgr)
    
    # Run Whisper in Reservation context
    with planner.acquire("whisper", 2 * 1024 * 1024 * 1024) as res:
        assert res.model_name == "whisper"
        assert res.allocated_vram_bytes == 2 * 1024 * 1024 * 1024
        assert res.active is True
        assert model_mgr.active_models["whisper"] == ModelLifecycleState.LOADED
        assert resources.allocated_vram_bytes == 2 * 1024 * 1024 * 1024
        
    # Verify Whisper auto-unloaded on exit
    assert model_mgr.active_models["whisper"] == ModelLifecycleState.EVICTED
    assert resources.allocated_vram_bytes == 0
    
    # Pinning a loaded model and expecting context managers to fail if VRAM is exceeded
    with planner.acquire("model_a", 3 * 1024 * 1024 * 1024):
        model_mgr.pin_model("model_a")
        
        # Trying to load Model B (2 GB) exceeds ceiling (3GB + 2GB > 4GB) and Model A is pinned
        with pytest.raises(ResourceAcquisitionError) as exc_info:
            with planner.acquire("model_b", 2 * 1024 * 1024 * 1024):
                pass
        assert "Cannot fit model" in str(exc_info.value)
        
    # Verify Model A is unloaded after outer context exit
    assert model_mgr.active_models["model_a"] == ModelLifecycleState.EVICTED
    assert resources.allocated_vram_bytes == 0
