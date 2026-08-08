import pytest
from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository

def test_di_registration_and_resolution():
    container = get_container()
    container.clear()
    
    repo = SQLiteGraphRepository(":memory:")
    container.register(GraphRepository, repo)
    
    resolved = container.resolve(GraphRepository)
    assert resolved is repo
    assert isinstance(resolved, SQLiteGraphRepository)

def test_di_unregistered_dependency():
    container = get_container()
    container.clear()
    
    with pytest.raises(ValueError) as exc_info:
        container.resolve(GraphRepository)
    assert "Dependency 'GraphRepository' has not been registered" in str(exc_info.value)
