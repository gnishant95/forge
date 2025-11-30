"""
Tests for Prometheus exporters.

These tests verify that metrics from exporters are being collected by Prometheus.
Exporters are internal to Docker and accessed via Prometheus scraping, not directly.
"""

import pytest


class TestMySQLExporterMetrics:
    """Tests for MySQL metrics in Prometheus."""

    def test_mysql_up_metric(self, http_client, prometheus_url):
        """Test that Prometheus has mysql_up metric."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "mysql_up"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        
        data = response.json()
        result = data.get("data", {}).get("result", [])
        
        assert len(result) > 0, "MySQL metrics not found in Prometheus - check mysql-exporter"
        
        # Check that mysql_up = 1 (healthy)
        for r in result:
            value = r.get("value", [None, "0"])[1]
            assert value == "1", f"MySQL exporter reports unhealthy: mysql_up = {value}"

    def test_mysql_connection_metrics(self, http_client, prometheus_url):
        """Test that MySQL connection metrics exist in Prometheus."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "mysql_global_status_threads_connected"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        data = response.json()
        assert data.get("status") == "success"

    def test_mysql_queries_metric(self, http_client, prometheus_url):
        """Test that MySQL queries metric exists."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "mysql_global_status_queries"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        data = response.json()
        assert data.get("status") == "success"


class TestRedisExporterMetrics:
    """Tests for Redis metrics in Prometheus."""

    def test_redis_up_metric(self, http_client, prometheus_url):
        """Test that Prometheus has redis_up metric."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "redis_up"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        
        data = response.json()
        result = data.get("data", {}).get("result", [])
        
        assert len(result) > 0, "Redis metrics not found in Prometheus - check redis-exporter"
        
        # Check that redis_up = 1 (healthy)
        for r in result:
            value = r.get("value", [None, "0"])[1]
            assert value == "1", f"Redis exporter reports unhealthy: redis_up = {value}"

    def test_redis_memory_metric(self, http_client, prometheus_url):
        """Test that Redis memory metric exists in Prometheus."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "redis_memory_used_bytes"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        data = response.json()
        assert data.get("status") == "success"

    def test_redis_connected_clients_metric(self, http_client, prometheus_url):
        """Test that Redis connected clients metric exists."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "redis_connected_clients"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        data = response.json()
        assert data.get("status") == "success"

    def test_redis_commands_metric(self, http_client, prometheus_url):
        """Test that Redis commands metric exists."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "redis_commands_total"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        data = response.json()
        assert data.get("status") == "success"


class TestNginxExporterMetrics:
    """Tests for Nginx metrics in Prometheus."""

    def test_nginx_up_metric(self, http_client, prometheus_url):
        """Test that Prometheus has nginx_up metric."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "nginx_up"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        
        data = response.json()
        result = data.get("data", {}).get("result", [])
        
        assert len(result) > 0, "Nginx metrics not found in Prometheus - check nginx-exporter"
        
        # Check that nginx_up = 1 (healthy)
        for r in result:
            value = r.get("value", [None, "0"])[1]
            assert value == "1", f"Nginx exporter reports unhealthy: nginx_up = {value}"

    def test_nginx_connections_metric(self, http_client, prometheus_url):
        """Test that Nginx connections metric exists in Prometheus."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "nginx_connections_active"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        data = response.json()
        assert data.get("status") == "success"

    def test_nginx_requests_metric(self, http_client, prometheus_url):
        """Test that Nginx requests metric exists."""
        response = http_client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "nginx_http_requests_total"}
        )
        
        assert response.status_code == 200, f"Prometheus query failed: {response.text}"
        data = response.json()
        assert data.get("status") == "success"


class TestPrometheusHealth:
    """Tests for Prometheus health and scraping."""

    def test_prometheus_is_running(self, http_client, prometheus_url):
        """Test that Prometheus is running and healthy."""
        response = http_client.get(f"{prometheus_url}/-/ready")
        assert response.status_code == 200, f"Prometheus not ready: {response.text}"

    def test_prometheus_targets(self, http_client, prometheus_url):
        """Test that Prometheus has configured targets."""
        response = http_client.get(f"{prometheus_url}/api/v1/targets")
        
        assert response.status_code == 200, f"Could not get Prometheus targets: {response.text}"
        
        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])
        
        assert len(targets) > 0, "No active Prometheus targets"

    def test_prometheus_scrape_health(self, http_client, prometheus_url):
        """Test that Prometheus targets are being scraped successfully."""
        response = http_client.get(f"{prometheus_url}/api/v1/targets")
        
        assert response.status_code == 200, f"Could not get Prometheus targets: {response.text}"
        
        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])
        
        # Count healthy vs unhealthy targets
        healthy = sum(1 for t in targets if t.get("health") == "up")
        total = len(targets)
        
        # At least some targets should be healthy
        assert healthy > 0, f"No healthy Prometheus targets (0/{total})"
        
        # Log the health status for debugging
        print(f"Prometheus targets: {healthy}/{total} healthy")
        
        for t in targets:
            if t.get("health") != "up":
                print(f"  Unhealthy: {t.get('labels', {}).get('job', 'unknown')} - {t.get('lastError', 'no error')}")


class TestExporterJobsInPrometheus:
    """Tests that verify exporter jobs are configured in Prometheus."""

    def test_mysql_job_exists(self, http_client, prometheus_url):
        """Test that mysql job is configured in Prometheus."""
        response = http_client.get(f"{prometheus_url}/api/v1/targets")
        
        assert response.status_code == 200, f"Could not get Prometheus targets: {response.text}"
        
        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])
        
        jobs = [t.get("labels", {}).get("job") for t in targets]
        assert "mysql" in jobs, "MySQL job not found in Prometheus targets"

    def test_redis_job_exists(self, http_client, prometheus_url):
        """Test that redis job is configured in Prometheus."""
        response = http_client.get(f"{prometheus_url}/api/v1/targets")
        
        assert response.status_code == 200, f"Could not get Prometheus targets: {response.text}"
        
        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])
        
        jobs = [t.get("labels", {}).get("job") for t in targets]
        assert "redis" in jobs, "Redis job not found in Prometheus targets"

    def test_nginx_job_exists(self, http_client, prometheus_url):
        """Test that nginx job is configured in Prometheus."""
        response = http_client.get(f"{prometheus_url}/api/v1/targets")
        
        assert response.status_code == 200, f"Could not get Prometheus targets: {response.text}"
        
        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])
        
        jobs = [t.get("labels", {}).get("job") for t in targets]
        assert "nginx" in jobs, "Nginx job not found in Prometheus targets"

    def test_forge_api_job_exists(self, http_client, prometheus_url):
        """Test that forge-api job is configured and healthy."""
        response = http_client.get(f"{prometheus_url}/api/v1/targets")
        
        assert response.status_code == 200, f"Could not get Prometheus targets: {response.text}"
        
        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])
        
        # forge-api should always be present
        api_targets = [t for t in targets if t.get("labels", {}).get("job") == "forge-api"]
        
        assert len(api_targets) > 0, "forge-api job not found in Prometheus targets"
        
        # API should be healthy
        for t in api_targets:
            assert t.get("health") == "up", f"forge-api target unhealthy: {t.get('lastError')}"
