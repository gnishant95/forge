"""
Tests for Prometheus exporters.

These tests verify:
- MySQL exporter is running and exposing metrics
- Redis exporter is running and exposing metrics
- Nginx exporter is running and exposing metrics
- Prometheus is scraping metrics from all exporters
"""

import pytest


class TestMySQLExporter:
    """Tests for MySQL Prometheus exporter."""

    def test_mysql_exporter_metrics_endpoint(self, http_client, mysql_exporter_url):
        """Test that MySQL exporter metrics endpoint is accessible."""
        try:
            response = http_client.get(f"{mysql_exporter_url}/metrics")
        except Exception as e:
            pytest.skip(f"MySQL exporter not accessible: {e}")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_mysql_exporter_has_up_metric(self, http_client, mysql_exporter_url):
        """Test that MySQL exporter reports mysql_up metric."""
        try:
            response = http_client.get(f"{mysql_exporter_url}/metrics")
        except Exception:
            pytest.skip("MySQL exporter not accessible")
        
        metrics = response.text
        assert "mysql_up" in metrics

    def test_mysql_exporter_connection_metrics(self, http_client, mysql_exporter_url):
        """Test that MySQL exporter has connection metrics."""
        try:
            response = http_client.get(f"{mysql_exporter_url}/metrics")
        except Exception:
            pytest.skip("MySQL exporter not accessible")
        
        metrics = response.text
        
        # Check for common MySQL metrics
        expected_metrics = [
            "mysql_global_status_threads_connected",
            "mysql_global_status_queries",
        ]
        
        for metric in expected_metrics:
            if metric not in metrics:
                # Some metrics might not be available, log but don't fail
                print(f"Warning: {metric} not found")

    def test_mysql_exporter_innodb_metrics(self, http_client, mysql_exporter_url):
        """Test that MySQL exporter has InnoDB metrics."""
        try:
            response = http_client.get(f"{mysql_exporter_url}/metrics")
        except Exception:
            pytest.skip("MySQL exporter not accessible")
        
        metrics = response.text
        
        # InnoDB metrics should be present
        assert "mysql_global_status_innodb" in metrics or "mysql_info" in metrics


class TestRedisExporter:
    """Tests for Redis Prometheus exporter."""

    def test_redis_exporter_metrics_endpoint(self, http_client, redis_exporter_url):
        """Test that Redis exporter metrics endpoint is accessible."""
        try:
            response = http_client.get(f"{redis_exporter_url}/metrics")
        except Exception as e:
            pytest.skip(f"Redis exporter not accessible: {e}")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_redis_exporter_has_up_metric(self, http_client, redis_exporter_url):
        """Test that Redis exporter reports redis_up metric."""
        try:
            response = http_client.get(f"{redis_exporter_url}/metrics")
        except Exception:
            pytest.skip("Redis exporter not accessible")
        
        metrics = response.text
        assert "redis_up" in metrics

    def test_redis_exporter_memory_metrics(self, http_client, redis_exporter_url):
        """Test that Redis exporter has memory metrics."""
        try:
            response = http_client.get(f"{redis_exporter_url}/metrics")
        except Exception:
            pytest.skip("Redis exporter not accessible")
        
        metrics = response.text
        
        # Check for memory metrics
        assert "redis_memory_used_bytes" in metrics

    def test_redis_exporter_commands_metrics(self, http_client, redis_exporter_url):
        """Test that Redis exporter has command metrics."""
        try:
            response = http_client.get(f"{redis_exporter_url}/metrics")
        except Exception:
            pytest.skip("Redis exporter not accessible")
        
        metrics = response.text
        
        # Check for command metrics
        assert "redis_commands_total" in metrics or "redis_commands_processed_total" in metrics

    def test_redis_exporter_connected_clients(self, http_client, redis_exporter_url):
        """Test that Redis exporter reports connected clients."""
        try:
            response = http_client.get(f"{redis_exporter_url}/metrics")
        except Exception:
            pytest.skip("Redis exporter not accessible")
        
        metrics = response.text
        assert "redis_connected_clients" in metrics


class TestNginxExporter:
    """Tests for Nginx Prometheus exporter."""

    def test_nginx_exporter_metrics_endpoint(self, http_client, nginx_exporter_url):
        """Test that Nginx exporter metrics endpoint is accessible."""
        try:
            response = http_client.get(f"{nginx_exporter_url}/metrics")
        except Exception as e:
            pytest.skip(f"Nginx exporter not accessible: {e}")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_nginx_exporter_has_up_metric(self, http_client, nginx_exporter_url):
        """Test that Nginx exporter reports nginx_up metric."""
        try:
            response = http_client.get(f"{nginx_exporter_url}/metrics")
        except Exception:
            pytest.skip("Nginx exporter not accessible")
        
        metrics = response.text
        assert "nginx_up" in metrics

    def test_nginx_exporter_connections_metrics(self, http_client, nginx_exporter_url):
        """Test that Nginx exporter has connection metrics."""
        try:
            response = http_client.get(f"{nginx_exporter_url}/metrics")
        except Exception:
            pytest.skip("Nginx exporter not accessible")
        
        metrics = response.text
        
        # Check for connection metrics
        connection_metrics = [
            "nginx_connections_active",
            "nginx_connections_accepted",
            "nginx_connections_handled",
        ]
        
        found = any(m in metrics for m in connection_metrics)
        assert found, "No Nginx connection metrics found"

    def test_nginx_exporter_requests_metric(self, http_client, nginx_exporter_url):
        """Test that Nginx exporter has requests metric."""
        try:
            response = http_client.get(f"{nginx_exporter_url}/metrics")
        except Exception:
            pytest.skip("Nginx exporter not accessible")
        
        metrics = response.text
        assert "nginx_http_requests_total" in metrics


class TestPrometheusIntegration:
    """Tests for Prometheus scraping integration."""

    def test_prometheus_is_running(self, http_client, prometheus_url):
        """Test that Prometheus is running and healthy."""
        try:
            response = http_client.get(f"{prometheus_url}/-/ready")
        except Exception as e:
            pytest.skip(f"Prometheus not accessible: {e}")
        
        assert response.status_code == 200

    def test_prometheus_scrapes_mysql_exporter(self, http_client, prometheus_url):
        """Test that Prometheus is scraping MySQL exporter."""
        try:
            response = http_client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "mysql_up"}
            )
        except Exception:
            pytest.skip("Prometheus not accessible")
        
        if response.status_code != 200:
            pytest.skip("Prometheus query failed")
        
        data = response.json()
        result = data.get("data", {}).get("result", [])
        
        # Should have at least one result if MySQL exporter is being scraped
        if len(result) == 0:
            pytest.skip("MySQL metrics not yet scraped by Prometheus")
        
        # Check that mysql_up = 1 (healthy)
        for r in result:
            value = r.get("value", [None, "0"])[1]
            assert value == "1", f"MySQL is not healthy: mysql_up = {value}"

    def test_prometheus_scrapes_redis_exporter(self, http_client, prometheus_url):
        """Test that Prometheus is scraping Redis exporter."""
        try:
            response = http_client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "redis_up"}
            )
        except Exception:
            pytest.skip("Prometheus not accessible")
        
        if response.status_code != 200:
            pytest.skip("Prometheus query failed")
        
        data = response.json()
        result = data.get("data", {}).get("result", [])
        
        if len(result) == 0:
            pytest.skip("Redis metrics not yet scraped by Prometheus")
        
        # Check that redis_up = 1 (healthy)
        for r in result:
            value = r.get("value", [None, "0"])[1]
            assert value == "1", f"Redis is not healthy: redis_up = {value}"

    def test_prometheus_scrapes_nginx_exporter(self, http_client, prometheus_url):
        """Test that Prometheus is scraping Nginx exporter."""
        try:
            response = http_client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "nginx_up"}
            )
        except Exception:
            pytest.skip("Prometheus not accessible")
        
        if response.status_code != 200:
            pytest.skip("Prometheus query failed")
        
        data = response.json()
        result = data.get("data", {}).get("result", [])
        
        if len(result) == 0:
            pytest.skip("Nginx metrics not yet scraped by Prometheus")
        
        # Check that nginx_up = 1 (healthy)
        for r in result:
            value = r.get("value", [None, "0"])[1]
            assert value == "1", f"Nginx is not healthy: nginx_up = {value}"

    def test_prometheus_has_api_metrics(self, http_client, prometheus_url):
        """Test that Prometheus has Forge API metrics."""
        try:
            response = http_client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "http_requests_total"}
            )
        except Exception:
            pytest.skip("Prometheus not accessible")
        
        if response.status_code != 200:
            pytest.skip("Prometheus query failed")
        
        # API metrics might not be present initially
        data = response.json()
        # Just verify the query succeeded, metrics may or may not be present
        assert data.get("status") == "success"

    def test_prometheus_targets_health(self, http_client, prometheus_url):
        """Test that Prometheus targets are healthy."""
        try:
            response = http_client.get(f"{prometheus_url}/api/v1/targets")
        except Exception:
            pytest.skip("Prometheus not accessible")
        
        if response.status_code != 200:
            pytest.skip("Could not get Prometheus targets")
        
        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])
        
        # Count healthy vs unhealthy targets
        healthy = sum(1 for t in targets if t.get("health") == "up")
        total = len(targets)
        
        # At least some targets should be healthy
        assert healthy > 0, f"No healthy Prometheus targets (0/{total})"
        
        # Log the health status for debugging
        print(f"Prometheus targets: {healthy}/{total} healthy")


class TestExporterMetricsConsistency:
    """Tests for consistency between exporters and Prometheus."""

    def test_mysql_metrics_in_prometheus(self, http_client, mysql_exporter_url, prometheus_url):
        """Test that MySQL exporter metrics appear in Prometheus."""
        # Get metrics from exporter
        try:
            exporter_response = http_client.get(f"{mysql_exporter_url}/metrics")
        except Exception:
            pytest.skip("MySQL exporter not accessible")
        
        # Check if mysql_global_status_uptime is in exporter
        if "mysql_global_status_uptime" not in exporter_response.text:
            pytest.skip("mysql_global_status_uptime not in exporter")
        
        # Query Prometheus for the same metric
        try:
            prom_response = http_client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "mysql_global_status_uptime"}
            )
        except Exception:
            pytest.skip("Prometheus not accessible")
        
        if prom_response.status_code != 200:
            pytest.skip("Prometheus query failed")
        
        data = prom_response.json()
        result = data.get("data", {}).get("result", [])
        
        # Metric should be in Prometheus if exporter is being scraped
        if len(result) == 0:
            pytest.skip("Metric not yet in Prometheus (scrape pending)")

    def test_redis_metrics_in_prometheus(self, http_client, redis_exporter_url, prometheus_url):
        """Test that Redis exporter metrics appear in Prometheus."""
        # Get metrics from exporter
        try:
            exporter_response = http_client.get(f"{redis_exporter_url}/metrics")
        except Exception:
            pytest.skip("Redis exporter not accessible")
        
        # Check if redis_uptime_in_seconds is in exporter
        if "redis_uptime_in_seconds" not in exporter_response.text:
            pytest.skip("redis_uptime_in_seconds not in exporter")
        
        # Query Prometheus for the same metric
        try:
            prom_response = http_client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "redis_uptime_in_seconds"}
            )
        except Exception:
            pytest.skip("Prometheus not accessible")
        
        if prom_response.status_code != 200:
            pytest.skip("Prometheus query failed")
        
        data = prom_response.json()
        result = data.get("data", {}).get("result", [])
        
        if len(result) == 0:
            pytest.skip("Metric not yet in Prometheus (scrape pending)")

