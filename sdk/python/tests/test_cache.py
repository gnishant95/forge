"""
Tests for Forge cache (Redis) operations.

These tests verify:
- Set, get, delete operations via SDK
- TTL expiration behavior
- Redis client integration
- Connection info retrieval
"""

import time
import pytest


class TestCacheBasicOperations:
    """Tests for basic cache operations."""

    def test_set_and_get(self, forge, cleanup_cache, test_id):
        """Test setting and getting a cache value."""
        key = f"test_key_{test_id}"
        value = "test_value"
        cleanup_cache.append(key)
        
        # Set value
        result = forge.cache.set(key, value)
        assert result is True
        
        # Get value
        retrieved = forge.cache.get(key)
        assert retrieved == value

    def test_get_nonexistent_key(self, forge, test_id):
        """Test getting a key that doesn't exist."""
        key = f"nonexistent_{test_id}"
        
        result = forge.cache.get(key)
        assert result is None

    def test_delete_key(self, forge, cleanup_cache, test_id):
        """Test deleting a cache key."""
        key = f"delete_test_{test_id}"
        cleanup_cache.append(key)
        
        # Set value
        forge.cache.set(key, "to_delete")
        
        # Delete
        result = forge.cache.delete(key)
        assert result is True
        
        # Verify deleted
        retrieved = forge.cache.get(key)
        assert retrieved is None

    def test_delete_nonexistent_key(self, forge, test_id):
        """Test deleting a key that doesn't exist."""
        key = f"nonexistent_delete_{test_id}"
        
        result = forge.cache.delete(key)
        # Should return False for non-existent key
        assert result is False

    def test_overwrite_value(self, forge, cleanup_cache, test_id):
        """Test overwriting an existing cache value."""
        key = f"overwrite_test_{test_id}"
        cleanup_cache.append(key)
        
        # Set initial value
        forge.cache.set(key, "initial")
        assert forge.cache.get(key) == "initial"
        
        # Overwrite
        forge.cache.set(key, "updated")
        assert forge.cache.get(key) == "updated"


class TestCacheTTL:
    """Tests for cache TTL (time-to-live) functionality."""

    @pytest.mark.slow
    def test_ttl_expiration(self, forge, test_id):
        """Test that keys expire after TTL."""
        key = f"ttl_test_{test_id}"
        
        # Set with 2 second TTL
        forge.cache.set(key, "expires_soon", ttl=2)
        
        # Should exist immediately
        assert forge.cache.get(key) == "expires_soon"
        
        # Wait for expiration
        time.sleep(3)
        
        # Should be gone
        assert forge.cache.get(key) is None

    def test_no_ttl_persists(self, forge, cleanup_cache, test_id):
        """Test that keys without TTL persist."""
        key = f"no_ttl_test_{test_id}"
        cleanup_cache.append(key)
        
        # Set without TTL (ttl=0 means no expiration)
        forge.cache.set(key, "persistent", ttl=0)
        
        # Should still exist after a short wait
        time.sleep(1)
        assert forge.cache.get(key) == "persistent"


class TestCacheDataTypes:
    """Tests for different data types in cache."""

    def test_string_value(self, forge, cleanup_cache, test_id):
        """Test caching string values."""
        key = f"string_test_{test_id}"
        cleanup_cache.append(key)
        
        value = "Hello, World!"
        forge.cache.set(key, value)
        
        assert forge.cache.get(key) == value

    def test_numeric_string(self, forge, cleanup_cache, test_id):
        """Test caching numeric strings."""
        key = f"numeric_test_{test_id}"
        cleanup_cache.append(key)
        
        value = "12345"
        forge.cache.set(key, value)
        
        assert forge.cache.get(key) == value

    def test_json_string(self, forge, cleanup_cache, test_id):
        """Test caching JSON strings."""
        import json
        
        key = f"json_test_{test_id}"
        cleanup_cache.append(key)
        
        data = {"name": "test", "values": [1, 2, 3]}
        value = json.dumps(data)
        
        forge.cache.set(key, value)
        
        retrieved = forge.cache.get(key)
        assert json.loads(retrieved) == data

    def test_unicode_value(self, forge, cleanup_cache, test_id):
        """Test caching unicode values."""
        key = f"unicode_test_{test_id}"
        cleanup_cache.append(key)
        
        value = "Hello 世界 🌍"
        forge.cache.set(key, value)
        
        assert forge.cache.get(key) == value

    def test_empty_string(self, forge, cleanup_cache, test_id):
        """Test caching empty string."""
        key = f"empty_test_{test_id}"
        cleanup_cache.append(key)
        
        forge.cache.set(key, "")
        
        # Empty string should be retrievable (not None)
        result = forge.cache.get(key)
        assert result == ""


class TestCacheInfo:
    """Tests for cache connection info."""

    def test_cache_url_format(self, forge):
        """Test that cache.url() returns proper Redis URL."""
        url = forge.cache.url()
        
        assert url is not None
        assert url.startswith("redis://")
        assert ":" in url  # Contains port


class TestRedisClientIntegration:
    """Tests for direct Redis client integration."""

    def test_get_redis_client(self, forge):
        """Test getting Redis client from SDK."""
        import redis
        
        client = forge.cache.client()
        
        assert client is not None
        
        # Test ping
        assert client.ping() is True

    def test_redis_client_operations(self, forge, test_id):
        """Test operations via Redis client."""
        import redis
        
        client = forge.cache.client()
        key = f"redis_client_test_{test_id}"
        
        try:
            # Set
            client.set(key, "direct_value")
            
            # Get
            value = client.get(key)
            assert value.decode() == "direct_value"
            
            # Delete
            client.delete(key)
            assert client.get(key) is None
        finally:
            # Cleanup
            client.delete(key)

    def test_redis_client_data_structures(self, forge, test_id):
        """Test Redis data structures via client."""
        import redis
        
        client = forge.cache.client()
        
        # Test list
        list_key = f"list_test_{test_id}"
        try:
            client.rpush(list_key, "a", "b", "c")
            assert client.lrange(list_key, 0, -1) == [b"a", b"b", b"c"]
        finally:
            client.delete(list_key)
        
        # Test hash
        hash_key = f"hash_test_{test_id}"
        try:
            client.hset(hash_key, mapping={"field1": "value1", "field2": "value2"})
            assert client.hget(hash_key, "field1") == b"value1"
        finally:
            client.delete(hash_key)
        
        # Test set
        set_key = f"set_test_{test_id}"
        try:
            client.sadd(set_key, "member1", "member2")
            members = client.smembers(set_key)
            assert b"member1" in members
            assert b"member2" in members
        finally:
            client.delete(set_key)


class TestCacheRESTAPI:
    """Tests for cache REST API directly."""

    def test_cache_set_via_rest(self, http_client, forge, cleanup_cache, test_id):
        """Test setting cache via REST API."""
        key = f"rest_set_test_{test_id}"
        cleanup_cache.append(key)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/cache/{key}",
            json={"value": "rest_value", "ttl": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True

    def test_cache_get_via_rest(self, http_client, forge, cleanup_cache, test_id):
        """Test getting cache via REST API."""
        key = f"rest_get_test_{test_id}"
        cleanup_cache.append(key)
        
        # Set first
        forge.cache.set(key, "rest_get_value")
        
        # Get via REST
        response = http_client.get(f"{forge.base_url}/api/v1/cache/{key}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("found") is True
        assert data.get("value") == "rest_get_value"

    def test_cache_delete_via_rest(self, http_client, forge, cleanup_cache, test_id):
        """Test deleting cache via REST API."""
        key = f"rest_delete_test_{test_id}"
        
        # Set first
        forge.cache.set(key, "to_delete")
        
        # Delete via REST
        response = http_client.delete(f"{forge.base_url}/api/v1/cache/{key}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("deleted") is True

    def test_cache_info_via_rest(self, http_client, forge):
        """Test getting cache info via REST API."""
        response = http_client.get(f"{forge.base_url}/api/v1/cache/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "host" in data
        assert "port" in data
        assert "url" in data

