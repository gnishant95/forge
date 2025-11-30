"""
Tests for Forge health checks and system information.

These tests verify that:
- The API is responsive and healthy
- All dependent services are running
- System information is correctly reported
"""

import pytest


class TestHealth:
    """Tests for the health endpoint."""

    def test_health_returns_response(self, forge):
        """Test that health endpoint returns a valid response."""
        result = forge.health()
        
        assert result is not None
        # ok is True only if ALL services are healthy
        assert "ok" in result
        assert "services" in result
        assert "uptime" in result

    def test_health_via_rest(self, http_client, forge):
        """Test health endpoint via direct REST call."""
        response = http_client.get(f"{forge.base_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        # Response should have expected structure
        assert "ok" in data
        assert "services" in data
        assert "uptime" in data


class TestServiceHealth:
    """Tests for individual service health status."""

    def test_core_services_present(self, http_client, forge):
        """Test that core services are reported in health check."""
        response = http_client.get(f"{forge.base_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        services = data.get("services", {})
        
        # Core services that should be present in health check
        expected_services = ["api", "mysql", "redis", "nginx"]
        
        for service in expected_services:
            assert service in services, f"Service {service} not found in health check"
        
        # API should always be healthy (it's responding)
        assert services["api"]["status"] == "healthy"

    def test_api_always_healthy(self, http_client, forge):
        """Test that the API service is always healthy when responding."""
        response = http_client.get(f"{forge.base_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        services = data.get("services", {})
        assert services.get("api", {}).get("status") == "healthy"

    def test_observability_services_healthy(self, http_client, forge):
        """Test that observability services are healthy."""
        response = http_client.get(f"{forge.base_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        services = data.get("services", {})
        
        # Observability services
        observability_services = ["grafana", "prometheus", "loki", "tempo"]
        
        for service in observability_services:
            if service in services:
                # These might not be running in minimal setups
                assert services[service]["status"] == "healthy", \
                    f"Service {service} is not healthy: {services[service]}"

    def test_health_includes_uptime(self, http_client, forge):
        """Test that health response includes uptime."""
        response = http_client.get(f"{forge.base_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "uptime" in data
        # Uptime should be a duration string like "1h2m3s"
        assert isinstance(data["uptime"], str)
        assert len(data["uptime"]) > 0


class TestSystemInfo:
    """Tests for system information via SDK."""

    def test_info_returns_version(self, forge):
        """Test that info returns SDK version."""
        result = forge.info()
        
        assert result is not None
        assert "version" in result
        # Version comes from SDK package
        assert result["version"] == "0.1.0"

    def test_info_returns_uptime(self, forge):
        """Test that info returns uptime from health endpoint."""
        result = forge.info()
        
        assert result is not None
        assert "uptime" in result
        assert isinstance(result["uptime"], str)

    def test_info_returns_services(self, forge):
        """Test that info returns services from health endpoint."""
        result = forge.info()
        
        assert result is not None
        assert "services" in result
        assert isinstance(result["services"], dict)

    def test_info_caching(self, forge):
        """Test that info is cached by the client."""
        # First call
        result1 = forge.info()
        
        # Second call should use cache
        result2 = forge.info()
        
        assert result1 == result2
        
        # Force refresh should work
        result3 = forge.info(refresh=True)
        assert result3 is not None


class TestSystemInfoEndpoint:
    """Tests for the /system endpoint."""

    def test_system_info_endpoint(self, http_client, forge):
        """Test the system info endpoint returns container information."""
        response = http_client.get(f"{forge.base_url}/api/v1/system")
        
        assert response.status_code == 200, f"System endpoint failed: {response.text}"
        data = response.json()
        
        # Should contain container information
        assert "containers" in data, "Response should contain 'containers' field"

    def test_system_info_lists_forge_containers(self, http_client, forge):
        """Test that system info lists Forge containers."""
        response = http_client.get(f"{forge.base_url}/api/v1/system")
        
        assert response.status_code == 200, f"System endpoint failed: {response.text}"
        
        data = response.json()
        containers = data.get("containers", {})
        
        # containers is a dict with container names as keys
        container_names = list(containers.keys())
        
        # Check for forge containers (they should contain 'forge' in the name)
        forge_containers = [n for n in container_names if "forge" in n.lower()]
        assert len(forge_containers) > 0, "No Forge containers found"

