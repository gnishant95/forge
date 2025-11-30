"""
Main Forge client
"""

import requests
from typing import Optional, Dict, Any

from .db import DatabaseClient
from .cache import CacheClient
from .observe import LogsClient, MetricsClient, TracesClient


class Forge:
    """
    Main Forge client providing access to all services.
    
    Usage:
        f = Forge("localhost")
        
        # Database
        result = f.db.query("SELECT * FROM users")
        engine = f.db.engine()  # SQLAlchemy engine
        
        # Cache
        f.cache.set("key", "value")
        value = f.cache.get("key")
        
        # Observability
        f.logs.info("User logged in", user_id=123)
        f.metrics.increment("requests_total")
    """
    
    def __init__(self, host: str = "localhost", port: int = 80):
        """
        Initialize Forge client.
        
        Args:
            host: Forge server hostname (default: localhost)
            port: Forge server port (default: 80)
        """
        # Handle host with path (e.g., "myserver.com/forge")
        if "/" in host:
            self.base_url = f"http://{host}"
        else:
            if port == 80:
                self.base_url = f"http://{host}"
            else:
                self.base_url = f"http://{host}:{port}"
        
        self._session = requests.Session()
        self._info_cache: Optional[Dict[str, Any]] = None
        
        # Initialize sub-clients
        self.db = DatabaseClient(self)
        self.cache = CacheClient(self)
        self.logs = LogsClient(self)
        self.metrics = MetricsClient(self)
        self.traces = TracesClient(self)
    
    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make HTTP request to Forge API."""
        url = f"{self.base_url}/api/v1{path}"
        response = self._session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    
    def health(self) -> Dict[str, bool]:
        """
        Check if Forge is healthy.
        
        Returns:
            {"ok": True} if healthy
        """
        response = self._request("GET", "/health")
        return response.json()
    
    def info(self, refresh: bool = False) -> Dict[str, Any]:
        """
        Get detailed system information.
        
        Args:
            refresh: Force refresh of cached info
            
        Returns:
            System info including version, uptime, and service statuses
        """
        if self._info_cache is None or refresh:
            response = self._request("GET", "/info")
            self._info_cache = response.json()
        return self._info_cache
    
    def __repr__(self) -> str:
        return f"Forge({self.base_url})"

