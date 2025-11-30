"""
Shared pytest fixtures for Forge SDK tests.

These tests are designed to run against a live Forge environment.
Start the environment with: docker compose --profile full up -d
"""

import os
import uuid
import pytest
import httpx

# Add parent directory to path to import forge SDK
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge import Forge


# Configuration - can be overridden via environment variables
FORGE_HOST = os.getenv("FORGE_HOST", "localhost")
FORGE_PORT = int(os.getenv("FORGE_PORT", "80"))

# Direct service ports for observability stack
# These are exposed to host and configurable via env
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
LOKI_PORT = int(os.getenv("LOKI_PORT", "3100"))


@pytest.fixture(scope="session")
def forge():
    """
    Create a Forge client for the test session.
    
    Returns:
        Forge: Configured Forge client
    """
    return Forge(host=FORGE_HOST, port=FORGE_PORT)


@pytest.fixture(scope="session")
def http_client():
    """
    Create an httpx client for direct API calls.
    
    Returns:
        httpx.Client: HTTP client for direct requests
    """
    with httpx.Client(timeout=30.0) as client:
        yield client


@pytest.fixture
def test_id():
    """
    Generate a unique test ID for test isolation.
    
    Returns:
        str: Unique identifier for this test run
    """
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_db_name(test_id):
    """
    Generate a unique test database name.
    
    Returns:
        str: Database name for this test
    """
    return f"forge_{test_id}"




@pytest.fixture
def cleanup_cache(forge, test_id):
    """
    Fixture that cleans up cache keys after test.
    
    Yields:
        list: List to track keys that need cleanup
    """
    keys_to_cleanup = []
    yield keys_to_cleanup
    
    # Cleanup after test
    for key in keys_to_cleanup:
        try:
            forge.cache.delete(key)
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture
def cleanup_db(forge, test_db_name):
    """
    Fixture that creates and cleans up a test database.
    
    Yields:
        str: The test database name
    """
    # Create test database
    forge.db.execute(f"CREATE DATABASE IF NOT EXISTS {test_db_name}")
    
    yield test_db_name
    
    # Cleanup after test
    try:
        forge.db.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture
def cleanup_routes(forge, test_id):
    """
    Fixture that cleans up routes after test.
    
    Yields:
        list: List to track routes that need cleanup
    """
    routes_to_cleanup = []
    yield routes_to_cleanup
    
    # Cleanup after test
    for route_name in routes_to_cleanup:
        try:
            forge._request("DELETE", f"/routes/{route_name}")
        except Exception:
            pass


@pytest.fixture
def cleanup_logsources(forge, test_id):
    """
    Fixture that cleans up log sources after test.
    
    Yields:
        list: List to track log sources that need cleanup
    """
    sources_to_cleanup = []
    yield sources_to_cleanup
    
    # Cleanup after test
    for source_name in sources_to_cleanup:
        try:
            forge._request("DELETE", f"/logs/sources/{source_name}")
        except Exception:
            pass


@pytest.fixture(scope="session")
def prometheus_url():
    """URL for direct Prometheus access."""
    return f"http://{FORGE_HOST}:{PROMETHEUS_PORT}"


@pytest.fixture(scope="session")
def loki_url():
    """URL for direct Loki access."""
    return f"http://{FORGE_HOST}:{LOKI_PORT}"


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end integration tests"
    )

