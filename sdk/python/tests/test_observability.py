"""
Tests for Forge observability features.

These tests verify:
- Pushing logs to Loki via SDK
- Pushing metrics via SDK
- Pushing traces via SDK
- Verification that logs appear in Loki
"""

import time
import pytest


class TestLogging:
    """Tests for log pushing functionality."""

    def test_log_info(self, forge, test_id):
        """Test pushing info log."""
        result = forge.logs.info(
            f"Test info message {test_id}",
            test_id=test_id,
            source="pytest"
        )
        
        assert result is True

    def test_log_debug(self, forge, test_id):
        """Test pushing debug log."""
        result = forge.logs.debug(
            f"Test debug message {test_id}",
            test_id=test_id
        )
        
        assert result is True

    def test_log_warning(self, forge, test_id):
        """Test pushing warning log."""
        result = forge.logs.warn(
            f"Test warning message {test_id}",
            test_id=test_id
        )
        
        assert result is True

    def test_log_warning_alias(self, forge, test_id):
        """Test pushing warning log using warning() alias."""
        result = forge.logs.warning(
            f"Test warning alias message {test_id}",
            test_id=test_id
        )
        
        assert result is True

    def test_log_error(self, forge, test_id):
        """Test pushing error log."""
        result = forge.logs.error(
            f"Test error message {test_id}",
            test_id=test_id,
            error_code="TEST_ERROR"
        )
        
        assert result is True

    def test_log_with_multiple_labels(self, forge, test_id):
        """Test pushing log with multiple labels."""
        result = forge.logs.info(
            f"Test with labels {test_id}",
            test_id=test_id,
            service="test_service",
            environment="test",
            version="1.0.0",
            user_id="12345"
        )
        
        assert result is True

    def test_log_via_rest(self, http_client, forge, test_id):
        """Test pushing log via REST API."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/logs",
            json={
                "message": f"REST log test {test_id}",
                "level": "info",
                "labels": {"test_id": test_id, "source": "rest_api"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True


class TestLogVerification:
    """Tests that verify logs appear in Loki."""

    @pytest.mark.slow
    def test_log_appears_in_loki(self, forge, http_client, loki_url, test_id):
        """Test that pushed logs can be queried from Loki."""
        # Push a unique log
        unique_marker = f"loki_verify_{test_id}"
        forge.logs.info(
            f"Verification test: {unique_marker}",
            test_id=test_id,
            verification="true"
        )
        
        # Retry querying Loki with backoff (logs take time to ingest)
        query = '{job="forge"} |= "' + unique_marker + '"'
        found = False
        last_error = None
        
        for attempt in range(5):  # Try 5 times
            time.sleep(2)  # Wait 2 seconds between attempts
            
            response = http_client.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "limit": 10,
                    "start": str(int((time.time() - 120) * 1e9)),  # Last 2 minutes
                    "end": str(int(time.time() * 1e9))
                }
            )
            
            assert response.status_code == 200, f"Loki query failed: {response.text}"
            
            data = response.json()
            result = data.get("data", {}).get("result", [])
            
            # Check if we found the log
            for stream in result:
                for value in stream.get("values", []):
                    if unique_marker in value[1]:
                        found = True
                        break
                if found:
                    break
            
            if found:
                break
        
        assert found, f"Log with marker '{unique_marker}' not found in Loki after 5 attempts"


class TestMetrics:
    """Tests for metrics pushing functionality."""

    def test_metric_increment(self, forge, test_id):
        """Test incrementing a counter metric."""
        result = forge.metrics.increment(
            f"test_counter_{test_id}",
            labels={"source": "pytest"}
        )
        
        assert result is True

    def test_metric_counter_alias(self, forge, test_id):
        """Test counter() alias for increment."""
        result = forge.metrics.counter(
            f"test_counter_alias_{test_id}",
            value=5,
            labels={"source": "pytest"}
        )
        
        assert result is True

    def test_metric_gauge(self, forge, test_id):
        """Test setting a gauge metric."""
        result = forge.metrics.gauge(
            f"test_gauge_{test_id}",
            value=42.5,
            labels={"source": "pytest"}
        )
        
        assert result is True

    def test_metric_histogram(self, forge, test_id):
        """Test recording a histogram observation."""
        result = forge.metrics.histogram(
            f"test_histogram_{test_id}",
            value=0.125,
            labels={"source": "pytest"}
        )
        
        assert result is True

    def test_metric_with_labels(self, forge, test_id):
        """Test metric with multiple labels."""
        result = forge.metrics.increment(
            f"test_labeled_counter_{test_id}",
            labels={
                "method": "GET",
                "path": "/api/test",
                "status": "200"
            }
        )
        
        assert result is True

    def test_metric_via_rest(self, http_client, forge, test_id):
        """Test pushing metric via REST API."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/metrics",
            json={
                "name": f"rest_metric_{test_id}",
                "value": 1.0,
                "type": "counter",
                "labels": {"source": "rest_api"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True


class TestTraces:
    """Tests for distributed tracing functionality."""

    def test_start_and_end_span(self, forge, test_id):
        """Test starting and ending a span."""
        span_id = forge.traces.start(
            name=f"test_operation_{test_id}",
            attributes={"test_id": test_id}
        )
        
        assert span_id is not None
        assert len(span_id) > 0
        
        # End the span
        result = forge.traces.end(span_id)
        assert result is True

    def test_span_with_trace_id(self, forge, test_id):
        """Test creating span with custom trace ID."""
        import uuid
        trace_id = uuid.uuid4().hex[:32]
        
        span_id = forge.traces.start(
            name=f"custom_trace_{test_id}",
            trace_id=trace_id,
            attributes={"custom": "true"}
        )
        
        assert span_id is not None
        
        # Verify span is tracked
        assert span_id in forge.traces._active_spans
        
        # End span
        forge.traces.end(span_id)

    def test_nested_spans(self, forge, test_id):
        """Test nested spans with parent-child relationship."""
        # Parent span
        parent_span_id = forge.traces.start(
            name=f"parent_operation_{test_id}"
        )
        
        # Child span
        child_span_id = forge.traces.start(
            name=f"child_operation_{test_id}",
            parent_span_id=parent_span_id
        )
        
        # End child first
        result1 = forge.traces.end(child_span_id)
        assert result1 is True
        
        # Then parent
        result2 = forge.traces.end(parent_span_id)
        assert result2 is True

    def test_end_nonexistent_span(self, forge):
        """Test ending a span that doesn't exist."""
        result = forge.traces.end("nonexistent_span_id")
        assert result is False

    def test_span_timing(self, forge, test_id):
        """Test that span captures timing information."""
        span_id = forge.traces.start(
            name=f"timed_operation_{test_id}"
        )
        
        # Simulate some work
        time.sleep(0.1)
        
        # The span should be tracked with start time
        assert span_id in forge.traces._active_spans
        span_data = forge.traces._active_spans[span_id]
        assert "start_time_ms" in span_data
        
        # End span
        forge.traces.end(span_id)

    def test_trace_via_rest(self, http_client, forge, test_id):
        """Test pushing trace via REST API."""
        import uuid
        
        trace_id = uuid.uuid4().hex[:32]
        span_id = uuid.uuid4().hex[:16]
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/traces",
            json={
                "name": f"rest_span_{test_id}",
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": "",
                "start_time_ms": int(time.time() * 1000) - 100,
                "duration_ms": 100,
                "attributes": {"source": "rest_api"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True


class TestObservabilityIntegration:
    """Integration tests for observability features."""

    def test_log_metrics_and_trace_together(self, forge, test_id):
        """Test using all observability features together."""
        # Start a trace
        span_id = forge.traces.start(
            name=f"integrated_operation_{test_id}",
            attributes={"test_id": test_id}
        )
        
        # Log the operation start
        forge.logs.info(
            f"Starting integrated operation {test_id}",
            test_id=test_id,
            span_id=span_id
        )
        
        # Record a metric
        forge.metrics.increment(
            "integrated_operations_total",
            labels={"test_id": test_id}
        )
        
        # Simulate operation
        time.sleep(0.05)
        
        # Record timing metric
        forge.metrics.histogram(
            "integrated_operation_duration",
            value=0.05,
            labels={"test_id": test_id}
        )
        
        # Log completion
        forge.logs.info(
            f"Completed integrated operation {test_id}",
            test_id=test_id,
            span_id=span_id,
            status="success"
        )
        
        # End trace
        result = forge.traces.end(span_id)
        assert result is True

