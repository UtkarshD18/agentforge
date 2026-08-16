import pytest
import httpx2 as httpx
import time

pytestmark = pytest.mark.resolve

def test_resolve_session_synchronization() -> None:
    """
    Test that the daemon host session POST and GET endpoints process Resolve snapshot metrics correctly.
    """
    daemon_url = "http://127.0.0.1:8888/api/v1/hosts/resolve/session"
    
    # Test payload mimicking Resolve UIManager panel output
    payload = {
        "host": "resolve",
        "connected": True,
        "project": {"name": "Nike Shorts Integration Test"},
        "timeline": {
            "name": "Edit Timeline V1",
            "fps": 30.0,
            "start_frame": 0,
            "end_frame": 1800,
            "clip_count": 12
        },
        "source": "resolve",
        "updated_at": time.time()
    }
    
    # Verify synchronization via HTTP client
    try:
        # POST state snapshot to daemon
        with httpx.Client(timeout=2.0) as client:
            post_resp = client.post(daemon_url, json=payload)
            assert post_resp.status_code == 200, f"Daemon POST failed: {post_resp.text}"
            
            # GET active state snapshot from daemon
            get_resp = client.get(daemon_url)
            assert get_resp.status_code == 200, f"Daemon GET failed: {get_resp.text}"
            
            data = get_resp.json()
            assert data["host"] == "resolve"
            assert data["connected"] is True
            assert data["project"]["name"] == "Nike Shorts Integration Test"
            assert data["timeline"]["clip_count"] == 12
            assert data["timeline"]["fps"] == 30.0
            
    except httpx.ConnectError:
        pytest.skip("FastAPI Daemon is offline. Start the daemon with uvicorn before running live integration tests.")
