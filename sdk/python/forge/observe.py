"""
Observability clients for Forge SDK
"""

from typing import Any, Dict, Optional, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from .client import Forge


class LogsClient:
    """
    Logs client for pushing logs to Loki.
    
    Usage:
        f = Forge("localhost")
        f.logs.info("User logged in", user_id=123)
        f.logs.error("Failed to process", error="timeout")
    """
    
    def __init__(self, forge: "Forge"):
        self._forge = forge
    
    def _push(self, level: str, message: str, **labels) -> bool:
        """Push a log entry."""
        payload = {
            "message": message,
            "level": level,
            "labels": {k: str(v) for k, v in labels.items()},
            "timestamp_ms": int(time.time() * 1000),
        }
        response = self._forge._request("POST", "/logs", json=payload)
        return response.json().get("ok", False)
    
    def debug(self, message: str, **labels) -> bool:
        """Log a debug message."""
        return self._push("debug", message, **labels)
    
    def info(self, message: str, **labels) -> bool:
        """Log an info message."""
        return self._push("info", message, **labels)
    
    def warn(self, message: str, **labels) -> bool:
        """Log a warning message."""
        return self._push("warn", message, **labels)
    
    def warning(self, message: str, **labels) -> bool:
        """Log a warning message (alias for warn)."""
        return self._push("warn", message, **labels)
    
    def error(self, message: str, **labels) -> bool:
        """Log an error message."""
        return self._push("error", message, **labels)
    
    def __repr__(self) -> str:
        return f"LogsClient()"


class MetricsClient:
    """
    Metrics client for pushing metrics to Prometheus.
    
    Usage:
        f = Forge("localhost")
        f.metrics.increment("requests_total", labels={"path": "/api"})
        f.metrics.gauge("active_users", 42)
    """
    
    def __init__(self, forge: "Forge"):
        self._forge = forge
    
    def _push(
        self,
        name: str,
        value: float,
        type: str,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Push a metric."""
        payload = {
            "name": name,
            "value": value,
            "type": type,
            "labels": labels or {},
        }
        response = self._forge._request("POST", "/metrics", json=payload)
        return response.json().get("ok", False)
    
    def increment(
        self,
        name: str,
        value: float = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Increment a counter metric."""
        return self._push(name, value, "counter", labels)
    
    def counter(
        self,
        name: str,
        value: float = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Increment a counter metric (alias for increment)."""
        return self._push(name, value, "counter", labels)
    
    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Set a gauge metric."""
        return self._push(name, value, "gauge", labels)
    
    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Record a histogram observation."""
        return self._push(name, value, "histogram", labels)
    
    def __repr__(self) -> str:
        return f"MetricsClient()"


class TracesClient:
    """
    Traces client for pushing traces to Tempo.
    
    Usage:
        f = Forge("localhost")
        span = f.traces.start("process_order")
        # ... do work ...
        f.traces.end(span)
    """
    
    def __init__(self, forge: "Forge"):
        self._forge = forge
        self._active_spans: Dict[str, Dict[str, Any]] = {}
    
    def start(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Start a new span.
        
        Args:
            name: Span name
            trace_id: Trace ID (generated if not provided)
            parent_span_id: Parent span ID (optional)
            attributes: Span attributes
            
        Returns:
            Span ID
        """
        import uuid
        
        span_id = str(uuid.uuid4())[:16]
        if trace_id is None:
            trace_id = str(uuid.uuid4())[:32]
        
        self._active_spans[span_id] = {
            "name": name,
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id or "",
            "start_time_ms": int(time.time() * 1000),
            "attributes": attributes or {},
        }
        
        return span_id
    
    def end(self, span_id: str) -> bool:
        """
        End a span and push to Tempo.
        
        Args:
            span_id: Span ID from start()
            
        Returns:
            True if successful
        """
        if span_id not in self._active_spans:
            return False
        
        span = self._active_spans.pop(span_id)
        end_time = int(time.time() * 1000)
        span["duration_ms"] = end_time - span["start_time_ms"]
        
        response = self._forge._request("POST", "/traces", json=span)
        return response.json().get("ok", False)
    
    def __repr__(self) -> str:
        return f"TracesClient()"

