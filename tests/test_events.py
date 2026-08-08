import asyncio
import pytest
from agentforge_core.events import Event, get_event_bus

def test_pydantic_event_schema():
    event = Event(event_type="test.event", payload={"key": "val"})
    assert event.event_type == "test.event"
    assert event.payload == {"key": "val"}
    assert event.version == "1.0"
    assert len(event.correlation_id) > 0
    assert event.timestamp > 0

def test_sync_subscription():
    received = []

    def callback(event: Event):
        received.append(event)

    bus = get_event_bus()
    bus.subscribe(callback)
    
    event = Event(event_type="workspace.created", payload={"id": "w1"})
    bus.publish(event)
    
    bus.unsubscribe(callback)
    
    assert len(received) == 1
    assert received[0].event_type == "workspace.created"
    assert received[0].payload == {"id": "w1"}

@pytest.mark.anyio
async def test_async_subscription():
    received = []
    future = asyncio.get_running_loop().create_future()

    async def callback(event: Event):
        received.append(event)
        future.set_result(True)

    bus = get_event_bus()
    bus.subscribe(callback)
    
    event = Event(event_type="task.completed", payload={"task_uri": "task://t1"})
    bus.publish(event)
    
    await future
    bus.unsubscribe(callback)
    
    assert len(received) == 1
    assert received[0].event_type == "task.completed"
    assert received[0].payload == {"task_uri": "task://t1"}
