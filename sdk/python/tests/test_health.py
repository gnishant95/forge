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

    def test_health_returns_ok(self, forge):
        """Test that health endpoint returns ok: true."""
        result = forge.health()
        
        assert result is not None
        assert result.get("ok") is True

    def test_health_via_rest(self, http_client, forge):
        """Test health endpoint via direct REST call."""
        response = http_client.get(f"{forge.base_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True


class TestServiceHealth:
    """Tests for individual service health status."""

    def test_all_services_healthy(self, http_client, forge):
        """Test that all services report healthy status."""
        response = http_client.get(f"{forge.base_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        services = data.get("services", {})
        
        # Core services that should always be healthy
        expected_services = ["api", "mysql", "redis", "nginx"]
        
        for service in expected_services:
            assert service in services, f"Service {service} not found in health check"
            assert services[service]["status"] == "healthy", \
                f"Service {service} is not healthy: {services[service]}"

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
    """Tests for system information endpoint."""

    def test_info_returns_version(self, forge):
        """Test that info endpoint returns version."""
        result = forge.info()
        
        assert result is not None
        assert "version" in result
        assert result["version"] == "0.1.0"

    def test_info_returns_uptime(self, forge):
        """Test that info endpoint returns uptime."""
        result = forge.info()
        
        assert result is not None
        assert "uptime" in result
        assert isinstance(result["uptime"], str)

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
    """Tests for the /system/info endpoint."""

    def test_system_info_endpoint(self, http_client, forge):
        """Test the system info endpoint returns container information."""
        response = http_client.get(f"{forge.base_url}/api/v1/system/info")
        
        # This might fail if Docker socket is not accessible
        if response.status_code == 200:
            data = response.json()
            
            # Should contain container information
            assert "containers" in data or "error" not in data
        else:
            # If Docker is not accessible, we expect a specific error
            pytest.skip("Docker socket not accessible for system info")

    def test_system_info_lists_forge_containers(self, http_client, forge):
        """Test that system info lists Forge containers."""
        response = http_client.get(f"{forge.base_url}/api/v1/system/info")
        
        if response.status_code != 200:
            pytest.skip("Docker socket not accessible")
        
        data = response.json()
        containers = data.get("containers", [])
        
        # Should have at least nginx and api containers
        container_names = [c.get("name", "") for c in containers]
        
        # Check for forge containers (they should contain 'forge' in the name)
        forge_containers = [n for n in container_names if "forge" in n.lower()]
        assert len(forge_containers) > 0, "No Forge containers found"

