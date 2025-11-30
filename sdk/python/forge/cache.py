"""
Cache client for Forge SDK
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Forge


class CacheClient:
    """
    Cache operations client.
    
    Usage:
        f = Forge("localhost")
        
        # Simple operations
        f.cache.set("key", "value", ttl=3600)
        value = f.cache.get("key")
        f.cache.delete("key")
        
        # Redis client integration
        redis = f.cache.client()
    """
    
    def __init__(self, forge: "Forge"):
        self._forge = forge
        self._info_cache: Optional[Dict[str, Any]] = None
    
    def get(self, key: str, type: str = "redis") -> Optional[str]:
        """
        Get a cached value.
        
        Args:
            key: Cache key
            type: Cache type (default: redis)
            
        Returns:
            Value if found, None otherwise
        """
        response = self._forge._request("GET", f"/cache/{key}")
        data = response.json()
        if data.get("found"):
            return data.get("value")
        return None
    
    def set(
        self,
        key: str,
        value: str,
        ttl: int = 0,
        type: str = "redis"
    ) -> bool:
        """
        Set a cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (0 = no expiry)
            type: Cache type (default: redis)
            
        Returns:
            True if successful
        """
        payload = {"value": value, "ttl": ttl}
        response = self._forge._request("POST", f"/cache/{key}", json=payload)
        return response.json().get("ok", False)
    
    def delete(self, key: str, type: str = "redis") -> bool:
        """
        Delete a cached value.
        
        Args:
            key: Cache key
            type: Cache type (default: redis)
            
        Returns:
            True if deleted, False if key didn't exist
        """
        response = self._forge._request("DELETE", f"/cache/{key}")
        return response.json().get("deleted", False)
    
    def _get_info(self) -> Dict[str, Any]:
        """Get cache connection info from API."""
        if self._info_cache is None:
            response = self._forge._request("GET", "/cache/info")
            self._info_cache = response.json()
        return self._info_cache
    
    def url(self) -> str:
        """
        Get Redis connection URL.
        
        Returns:
            Connection URL like "redis://host:port"
        """
        info = self._get_info()
        return info.get("url", "redis://localhost:6379")
    
    def client(self, **kwargs):
        """
        Get Redis client.
        
        Args:
            **kwargs: Additional arguments passed to Redis client
            
        Returns:
            Redis client instance
        """
        try:
            import redis
        except ImportError:
            raise ImportError(
                "redis is required for client(). "
                "Install it with: pip install redis"
            )
        
        info = self._get_info()
        return redis.Redis(
            host=info.get("host", "localhost"),
            port=info.get("port", 6379),
            password=info.get("password") or None,
            **kwargs
        )
    
    def __repr__(self) -> str:
        return f"CacheClient()"

