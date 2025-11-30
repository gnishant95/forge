"""
Database client for Forge SDK
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Forge


class DatabaseClient:
    """
    Database operations client.
    
    Usage:
        f = Forge("localhost")
        
        # Simple queries
        result = f.db.query("SELECT * FROM users")
        f.db.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])
        
        # SQLAlchemy integration
        engine = f.db.engine()
        engine = f.db.engine(database="mydb")
        
        # Get connection URL
        url = f.db.url()
    """
    
    def __init__(self, forge: "Forge"):
        self._forge = forge
        self._info_cache: Optional[Dict[str, Any]] = None
    
    def query(
        self,
        sql: str,
        params: Optional[List[str]] = None,
        database: Optional[str] = None,
        type: str = "mysql"
    ) -> Dict[str, Any]:
        """
        Execute a SELECT query.
        
        Args:
            sql: SQL query string
            params: Query parameters
            database: Database name (optional)
            type: Database type (default: mysql)
            
        Returns:
            Query results with rows, columns, and row_count
        """
        payload = {
            "sql": sql,
            "params": params or [],
            "database": database or "",
            "type": type,
        }
        response = self._forge._request("POST", "/db/query", json=payload)
        return response.json()
    
    def execute(
        self,
        sql: str,
        params: Optional[List[str]] = None,
        database: Optional[str] = None,
        type: str = "mysql"
    ) -> Dict[str, Any]:
        """
        Execute an INSERT/UPDATE/DELETE statement.
        
        Args:
            sql: SQL statement
            params: Statement parameters
            database: Database name (optional)
            type: Database type (default: mysql)
            
        Returns:
            Result with rows_affected and last_insert_id
        """
        payload = {
            "sql": sql,
            "params": params or [],
            "database": database or "",
            "type": type,
        }
        response = self._forge._request("POST", "/db/execute", json=payload)
        return response.json()
    
    def _get_info(self) -> Dict[str, Any]:
        """Get database connection info from API."""
        if self._info_cache is None:
            response = self._forge._request("GET", "/db/info")
            self._info_cache = response.json()
        return self._info_cache
    
    def url(self, database: Optional[str] = None) -> str:
        """
        Get SQLAlchemy connection URL.
        
        Args:
            database: Database name (optional)
            
        Returns:
            Connection URL like "mysql+pymysql://user:pass@host:port/db"
        """
        info = self._get_info()
        url = info.get("url", "")
        if database:
            url = f"{url}/{database}"
        return url
    
    def engine(self, database: Optional[str] = None, **kwargs):
        """
        Get SQLAlchemy Engine.
        
        Args:
            database: Database name (optional)
            **kwargs: Additional arguments passed to create_engine
            
        Returns:
            SQLAlchemy Engine instance
        """
        try:
            from sqlalchemy import create_engine
        except ImportError:
            raise ImportError(
                "SQLAlchemy is required for engine(). "
                "Install it with: pip install sqlalchemy pymysql"
            )
        
        url = self.url(database)
        return create_engine(url, **kwargs)
    
    def __repr__(self) -> str:
        return f"DatabaseClient()"

