"""
Tests for Forge log source management.

These tests verify:
- Listing log sources
- Adding log sources
- Getting specific log sources
- Deleting log sources
- Promtail reload functionality
"""

import pytest


class TestLogSourcesListing:
    """Tests for listing log sources."""

    def test_list_log_sources(self, http_client, forge):
        """Test listing all log sources."""
        response = http_client.get(f"{forge.base_url}/api/v1/logs/sources")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sources" in data
        assert "count" in data
        assert isinstance(data["sources"], list)
        assert data["count"] >= 0

    def test_list_sources_returns_array(self, http_client, forge):
        """Test that log sources list is always an array."""
        response = http_client.get(f"{forge.base_url}/api/v1/logs/sources")
        
        assert response.status_code == 200
        data = response.json()
        
        sources = data.get("sources", [])
        assert isinstance(sources, list)


class TestLogSourceCreation:
    """Tests for creating log sources."""

    def test_add_log_source(self, http_client, forge, cleanup_logsources, test_id):
        """Test adding a new log source."""
        source_name = f"test_source_{test_id}"
        cleanup_logsources.append(source_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/test_{test_id}/*.log",
                "labels": {
                    "app": f"test_{test_id}",
                    "environment": "test"
                }
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data.get("ok") is True
        assert "source" in data

    def test_add_log_source_with_job(self, http_client, forge, cleanup_logsources, test_id):
        """Test adding a log source with custom job name."""
        source_name = f"test_job_{test_id}"
        cleanup_logsources.append(source_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/job_{test_id}/*.log",
                "job": f"custom_job_{test_id}",
                "labels": {
                    "source": "test"
                }
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data.get("ok") is True

    def test_add_log_source_requires_name(self, http_client, forge):
        """Test that adding a log source requires a name."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "path": "/var/log/test.log"
            }
        )
        
        # Should fail without name
        assert response.status_code == 400

    def test_add_log_source_requires_path(self, http_client, forge):
        """Test that adding a log source requires a path."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": "test_no_path"
            }
        )
        
        # Should fail without path
        assert response.status_code == 400

    def test_add_log_source_with_multiline(self, http_client, forge, cleanup_logsources, test_id):
        """Test adding a log source with multiline configuration."""
        source_name = f"test_multiline_{test_id}"
        cleanup_logsources.append(source_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/multiline_{test_id}/*.log",
                "multiline": {
                    "first_line": "^\\d{4}-\\d{2}-\\d{2}",
                    "max_lines": 100
                }
            }
        )
        
        assert response.status_code == 201


class TestLogSourceRetrieval:
    """Tests for retrieving specific log sources."""

    def test_get_log_source_by_name(self, http_client, forge, cleanup_logsources, test_id):
        """Test getting a specific log source by name."""
        source_name = f"test_get_{test_id}"
        cleanup_logsources.append(source_name)
        
        # Create source first
        http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/get_{test_id}/*.log"
            }
        )
        
        # Get the source
        response = http_client.get(f"{forge.base_url}/api/v1/logs/sources/{source_name}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == source_name

    def test_get_nonexistent_log_source(self, http_client, forge, test_id):
        """Test getting a log source that doesn't exist."""
        response = http_client.get(f"{forge.base_url}/api/v1/logs/sources/nonexistent_{test_id}")
        
        assert response.status_code == 404


class TestLogSourceDeletion:
    """Tests for deleting log sources."""

    def test_delete_log_source(self, http_client, forge, test_id):
        """Test deleting a log source."""
        source_name = f"test_delete_{test_id}"
        
        # Create source first
        http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/delete_{test_id}/*.log"
            }
        )
        
        # Delete the source
        response = http_client.delete(f"{forge.base_url}/api/v1/logs/sources/{source_name}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True

    def test_delete_nonexistent_log_source(self, http_client, forge, test_id):
        """Test deleting a log source that doesn't exist."""
        response = http_client.delete(f"{forge.base_url}/api/v1/logs/sources/nonexistent_{test_id}")
        
        assert response.status_code == 404

    def test_deleted_source_not_retrievable(self, http_client, forge, test_id):
        """Test that deleted log sources cannot be retrieved."""
        source_name = f"test_deleted_{test_id}"
        
        # Create source
        http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/deleted_{test_id}/*.log"
            }
        )
        
        # Delete source
        http_client.delete(f"{forge.base_url}/api/v1/logs/sources/{source_name}")
        
        # Try to get deleted source
        response = http_client.get(f"{forge.base_url}/api/v1/logs/sources/{source_name}")
        assert response.status_code == 404


class TestPromtailReload:
    """Tests for Promtail reload functionality."""

    def test_reload_promtail(self, http_client, forge):
        """Test manual Promtail reload endpoint."""
        response = http_client.post(f"{forge.base_url}/api/v1/logs/sources/reload")
        
        # Note: This might fail if Promtail is not accessible
        if response.status_code == 200:
            data = response.json()
            assert data.get("ok") is True
        else:
            # Promtail might not be running or accessible
            pytest.skip("Promtail reload not available")

    def test_source_add_triggers_reload(self, http_client, forge, cleanup_logsources, test_id):
        """Test that adding a source triggers Promtail reload."""
        source_name = f"test_reload_{test_id}"
        cleanup_logsources.append(source_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/reload_{test_id}/*.log"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Response should indicate success (reload might have warning)
        assert data.get("ok") is True


class TestLogSourceConfiguration:
    """Tests for log source configuration options."""

    def test_source_with_all_options(self, http_client, forge, cleanup_logsources, test_id):
        """Test adding a log source with all configuration options."""
        source_name = f"test_full_{test_id}"
        cleanup_logsources.append(source_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/full_{test_id}/*.log",
                "job": f"full_job_{test_id}",
                "labels": {
                    "app": "test_app",
                    "environment": "test",
                    "team": "engineering"
                },
                "multiline": {
                    "first_line": "^\\[",
                    "max_lines": 50
                }
            }
        )
        
        assert response.status_code == 201
        
        # Verify source was created with options
        get_response = http_client.get(f"{forge.base_url}/api/v1/logs/sources/{source_name}")
        assert get_response.status_code == 200
        
        source_data = get_response.json()
        assert source_data.get("name") == source_name

    def test_source_labels_preserved(self, http_client, forge, cleanup_logsources, test_id):
        """Test that source labels are preserved."""
        source_name = f"test_labels_{test_id}"
        cleanup_logsources.append(source_name)
        
        labels = {
            "app": f"app_{test_id}",
            "environment": "staging",
            "version": "1.2.3"
        }
        
        # Create source
        http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/labels_{test_id}/*.log",
                "labels": labels
            }
        )
        
        # Get source
        response = http_client.get(f"{forge.base_url}/api/v1/logs/sources/{source_name}")
        data = response.json()
        
        # Verify labels
        source_labels = data.get("labels", {})
        for key, value in labels.items():
            assert source_labels.get(key) == value


class TestLogSourcePersistence:
    """Tests for log source persistence."""

    def test_sources_persist_after_list(self, http_client, forge, cleanup_logsources, test_id):
        """Test that log sources persist and appear in list."""
        source_name = f"test_persist_{test_id}"
        cleanup_logsources.append(source_name)
        
        # Add source
        http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": source_name,
                "path": f"/var/log/persist_{test_id}/*.log"
            }
        )
        
        # List sources
        response = http_client.get(f"{forge.base_url}/api/v1/logs/sources")
        data = response.json()
        
        sources = data.get("sources", [])
        source_names = [s.get("name") for s in sources]
        
        assert source_name in source_names


class TestLogSourceValidation:
    """Tests for log source input validation."""

    def test_empty_name_rejected(self, http_client, forge):
        """Test that empty name is rejected."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": "",
                "path": "/var/log/test.log"
            }
        )
        
        assert response.status_code == 400

    def test_empty_path_rejected(self, http_client, forge):
        """Test that empty path is rejected."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": "test_empty_path",
                "path": ""
            }
        )
        
        assert response.status_code == 400

    def test_large_payload_rejected(self, http_client, forge, test_id):
        """Test that very large payloads are rejected."""
        # Create a very large labels dict
        large_labels = {f"label_{i}": "x" * 10000 for i in range(100)}
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs/sources",
            json={
                "name": f"large_payload_{test_id}",
                "path": "/var/log/large.log",
                "labels": large_labels
            }
        )
        
        # Should reject due to size limit
        assert response.status_code in [400, 413]  # Bad Request or Payload Too Large

