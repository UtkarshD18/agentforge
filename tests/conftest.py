import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../examples")))
from resolve_smoke_test import connect_to_resolve

@pytest.fixture(scope="session")
def resolve_connection():
    """
    Session-scoped fixture providing a connection to the active Resolve scripting API.
    Gracefully skips tests if Resolve is offline.
    """
    try:
        resolve = connect_to_resolve()
        return resolve
    except RuntimeError as re:
        pytest.skip(f"Live DaVinci Resolve integration unavailable: {re}")
