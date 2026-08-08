import pytest

pytestmark = pytest.mark.resolve

def test_resolve_live_connection(resolve_connection) -> None:
    assert resolve_connection is not None, "Resolve connection object is None."
    project_manager = resolve_connection.GetProjectManager()
    assert project_manager is not None, "Failed to get ProjectManager."
