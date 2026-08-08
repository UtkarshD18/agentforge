import json
import os
import pytest
from fastapi.testclient import TestClient
from agentforge_runtime.main import app

# Cleanup database helper
@pytest.fixture(autouse=True)
def cleanup_db():
    # Remove agentforge.db if created during test lifespan runs
    db_file = "agentforge.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    yield
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

def test_create_and_get_workspace():
    """
    Verifies that the workspace creation POST and retrieval GET routes work.
    """
    with TestClient(app) as client:
        # Create workspace
        resp = client.post("/api/v1/workspace", json={"name": "Studio workspace", "metadata": {"type": "movie"}})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Studio workspace"
        assert data["metadata"]["type"] == "movie"
        assert data["uri"].startswith("workspace://")

        # Retrieve workspace
        workspace_id = data["uri"].split("/")[-1]
        resp_get = client.get(f"/api/v1/workspace/{workspace_id}")
        assert resp_get.status_code == 200
        data_get = resp_get.json()
        assert data_get["uri"] == data["uri"]
        assert data_get["name"] == "Studio workspace"

def test_websocket_event_broadcaster():
    """
    Verifies that publishing an event on the Event Bus broadcasts it to active WebSockets.
    """
    from agentforge_core.events import Event, get_event_bus

    with TestClient(app) as client:
        with client.websocket_connect("/ws/v1/events") as websocket:
            # Publish event on backend bus
            bus = get_event_bus()
            event = Event(event_type="agent.thinking", payload={"agent_id": "a-9", "tokens": 512})
            bus.publish(event)
            
            # Read text broadcast from the WebSocket client
            data = websocket.receive_text()
            event_data = json.loads(data)
            assert event_data["event_type"] == "agent.thinking"
            assert event_data["payload"] == {"agent_id": "a-9", "tokens": 512}
            assert len(event_data["correlation_id"]) > 0
