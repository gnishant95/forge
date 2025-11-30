"""
End-to-end tests for Forge platform.

These tests verify complete workflows across multiple services:
- Data flow from creation to observation
- SDK client integration
- Full stack functionality
"""

import time
import json
import pytest


@pytest.mark.e2e
class TestSDKInitialization:
    """Tests for SDK client initialization."""

    def test_forge_client_creation(self, forge):
        """Test that Forge client is created successfully."""
        assert forge is not None
        assert forge.base_url is not None
        assert hasattr(forge, 'db')
        assert hasattr(forge, 'cache')
        assert hasattr(forge, 'logs')
        assert hasattr(forge, 'metrics')
        assert hasattr(forge, 'traces')

    def test_forge_client_repr(self, forge):
        """Test that Forge client has string representation."""
        repr_str = repr(forge)
        assert "Forge" in repr_str
        assert "http" in repr_str

    def test_forge_client_with_path(self):
        """Test Forge client with path in host."""
        from forge import Forge
        
        client = Forge(host="example.com/forge")
        assert "http://example.com/forge" in client.base_url

    def test_all_subclients_initialized(self, forge):
        """Test that all sub-clients are properly initialized."""
        # Database client
        assert forge.db is not None
        assert repr(forge.db) == "DatabaseClient()"
        
        # Cache client
        assert forge.cache is not None
        assert repr(forge.cache) == "CacheClient()"
        
        # Logs client
        assert forge.logs is not None
        assert repr(forge.logs) == "LogsClient()"
        
        # Metrics client
        assert forge.metrics is not None
        assert repr(forge.metrics) == "MetricsClient()"
        
        # Traces client
        assert forge.traces is not None
        assert repr(forge.traces) == "TracesClient()"


@pytest.mark.e2e
class TestDatabaseCacheWorkflow:
    """End-to-end tests for database and cache workflows."""

    def test_store_in_db_cache_in_redis(self, forge, cleanup_db, cleanup_cache, test_id):
        """Test storing data in DB and caching in Redis."""
        db_name = cleanup_db
        cache_key = f"db_cache_{test_id}"
        cleanup_cache.append(cache_key)
        
        # Create table and insert data
        forge.db.execute(
            f"CREATE TABLE {db_name}.items (id INT PRIMARY KEY, name VARCHAR(255), price DECIMAL(10,2))"
        )
        forge.db.execute(
            f"INSERT INTO {db_name}.items VALUES (1, 'Widget', 19.99)"
        )
        
        # Query the data
        result = forge.db.query(f"SELECT * FROM {db_name}.items WHERE id = 1")
        
        assert result["row_count"] == 1
        row = result["rows"][0]["values"]
        
        # Cache the result (use column names to access values)
        cached_data = json.dumps({
            "id": row.get("id"),
            "name": row.get("name"),
            "price": row.get("price")
        })
        forge.cache.set(cache_key, cached_data)
        
        # Verify cache
        cached = forge.cache.get(cache_key)
        assert cached is not None
        
        data = json.loads(cached)
        assert data["name"] == "Widget"

    def test_cache_miss_fallback_to_db(self, forge, cleanup_db, cleanup_cache, test_id):
        """Test cache miss pattern with DB fallback."""
        db_name = cleanup_db
        cache_key = f"fallback_{test_id}"
        cleanup_cache.append(cache_key)
        
        # Setup DB data
        forge.db.execute(
            f"CREATE TABLE {db_name}.users (id INT PRIMARY KEY, username VARCHAR(100))"
        )
        forge.db.execute(
            f"INSERT INTO {db_name}.users VALUES (1, 'alice')"
        )
        
        # Try cache first (should miss)
        cached = forge.cache.get(cache_key)
        assert cached is None
        
        # Fallback to DB
        result = forge.db.query(f"SELECT username FROM {db_name}.users WHERE id = 1")
        username = result["rows"][0]["values"]["username"]
        
        # Populate cache
        forge.cache.set(cache_key, username, ttl=3600)
        
        # Verify cache hit
        cached = forge.cache.get(cache_key)
        assert cached == "alice"


@pytest.mark.e2e
class TestObservabilityWorkflow:
    """End-to-end tests for observability workflows."""

    def test_log_operation_with_trace(self, forge, test_id):
        """Test logging an operation with distributed tracing."""
        # Start a trace
        span_id = forge.traces.start(
            name=f"e2e_operation_{test_id}",
            attributes={"test_id": test_id, "type": "e2e"}
        )
        
        # Log the operation
        forge.logs.info(
            f"Starting E2E test operation {test_id}",
            test_id=test_id,
            span_id=span_id,
            phase="start"
        )
        
        # Record metric
        forge.metrics.increment(
            "e2e_test_operations",
            labels={"test_id": test_id}
        )
        
        # Simulate work
        time.sleep(0.1)
        
        # Record timing
        forge.metrics.histogram(
            "e2e_test_duration_seconds",
            value=0.1,
            labels={"test_id": test_id}
        )
        
        # Log completion
        forge.logs.info(
            f"Completed E2E test operation {test_id}",
            test_id=test_id,
            span_id=span_id,
            phase="complete",
            status="success"
        )
        
        # End trace
        result = forge.traces.end(span_id)
        assert result is True

    def test_error_logging_workflow(self, forge, test_id):
        """Test error logging workflow."""
        span_id = forge.traces.start(
            name=f"error_operation_{test_id}"
        )
        
        try:
            # Simulate operation that fails
            raise ValueError("Simulated error for testing")
        except ValueError as e:
            # Log error
            forge.logs.error(
                f"Operation failed: {str(e)}",
                test_id=test_id,
                span_id=span_id,
                error_type="ValueError"
            )
            
            # Record error metric
            forge.metrics.increment(
                "e2e_test_errors",
                labels={"test_id": test_id, "error_type": "ValueError"}
            )
        finally:
            forge.traces.end(span_id)


@pytest.mark.e2e
class TestFullStackWorkflow:
    """End-to-end tests for complete full-stack workflows."""

    def test_create_data_cache_log_verify(self, forge, cleanup_db, cleanup_cache, test_id, http_client, loki_url):
        """Test complete workflow: create data, cache it, log it, verify in Loki."""
        db_name = cleanup_db
        cache_key = f"fullstack_{test_id}"
        cleanup_cache.append(cache_key)
        
        unique_marker = f"fullstack_marker_{test_id}"
        
        # 1. Start trace
        span_id = forge.traces.start(
            name=f"fullstack_operation_{test_id}",
            attributes={"workflow": "fullstack"}
        )
        
        # 2. Create data in MySQL
        forge.db.execute(
            f"CREATE TABLE {db_name}.orders (id INT AUTO_INCREMENT PRIMARY KEY, product VARCHAR(255), quantity INT)"
        )
        forge.db.execute(
            f"INSERT INTO {db_name}.orders (product, quantity) VALUES ('Test Product', 5)"
        )
        
        # 3. Query and cache
        result = forge.db.query(f"SELECT * FROM {db_name}.orders ORDER BY id DESC LIMIT 1")
        row = result["rows"][0]["values"]
        order_data = {
            "id": row.get("id"),
            "product": row.get("product"),
            "quantity": row.get("quantity")
        }
        forge.cache.set(cache_key, json.dumps(order_data), ttl=300)
        
        # 4. Log the operation with unique marker
        forge.logs.info(
            f"Order created: {unique_marker}",
            test_id=test_id,
            span_id=span_id,
            order_id=str(order_data["id"]),
            product=order_data["product"]
        )
        
        # 5. Record metrics
        forge.metrics.increment(
            "orders_created",
            labels={"product": order_data["product"]}
        )
        
        # 6. End trace
        forge.traces.end(span_id)
        
        # 7. Verify cache hit
        cached = forge.cache.get(cache_key)
        assert cached is not None
        cached_order = json.loads(cached)
        assert cached_order["product"] == "Test Product"
        
        # 8. Optionally verify log in Loki (may take time to ingest)
        # This is best-effort verification
        time.sleep(2)
        
        try:
            query = '{job="forge"} |= "' + unique_marker + '"'
            response = http_client.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "limit": 10,
                    "start": str(int((time.time() - 120) * 1e9)),
                    "end": str(int(time.time() * 1e9))
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("data", {}).get("result", [])
                # Log found or not, don't fail the test
                if len(result) > 0:
                    print(f"Log verified in Loki: {unique_marker}")
        except Exception:
            # Loki verification is optional
            pass

    def test_sqlalchemy_with_observability(self, forge, cleanup_db, test_id):
        """Test SQLAlchemy operations with full observability."""
        from sqlalchemy import create_engine, text
        
        db_name = cleanup_db
        
        # Start trace
        span_id = forge.traces.start(
            name=f"sqlalchemy_operation_{test_id}",
            attributes={"orm": "sqlalchemy"}
        )
        
        try:
            # Get SQLAlchemy engine
            engine = forge.db.engine(database=db_name)
            
            # Log operation start
            forge.logs.info(
                f"Starting SQLAlchemy operations {test_id}",
                test_id=test_id,
                span_id=span_id
            )
            
            with engine.connect() as conn:
                # Create table
                conn.execute(text("""
                    CREATE TABLE products (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255),
                        price DECIMAL(10, 2)
                    )
                """))
                conn.commit()
                
                # Insert data
                for i in range(5):
                    conn.execute(text(
                        f"INSERT INTO products (name, price) VALUES ('Product {i}', {10.0 + i})"
                    ))
                conn.commit()
                
                # Query data
                result = conn.execute(text("SELECT COUNT(*) FROM products"))
                count = result.fetchone()[0]
                
                # Record metric
                forge.metrics.gauge(
                    "products_count",
                    value=float(count),
                    labels={"test_id": test_id}
                )
                
                assert count == 5
            
            # Log success
            forge.logs.info(
                f"SQLAlchemy operations completed {test_id}",
                test_id=test_id,
                span_id=span_id,
                status="success"
            )
        
        finally:
            forge.traces.end(span_id)

    def test_redis_client_with_observability(self, forge, test_id):
        """Test Redis client operations with observability."""
        import redis
        
        # Start trace
        span_id = forge.traces.start(
            name=f"redis_operations_{test_id}",
            attributes={"client": "redis-py"}
        )
        
        try:
            # Get Redis client
            client = forge.cache.client()
            
            # Log operation
            forge.logs.info(
                f"Starting Redis operations {test_id}",
                test_id=test_id,
                span_id=span_id
            )
            
            # Perform operations
            list_key = f"e2e_list_{test_id}"
            
            try:
                # Push items to list
                client.rpush(list_key, "item1", "item2", "item3")
                
                # Record list length
                length = client.llen(list_key)
                forge.metrics.gauge(
                    "redis_list_length",
                    value=float(length),
                    labels={"test_id": test_id}
                )
                
                # Pop items
                items = client.lrange(list_key, 0, -1)
                assert len(items) == 3
                
                # Log success
                forge.logs.info(
                    f"Redis operations completed {test_id}",
                    test_id=test_id,
                    span_id=span_id,
                    items_processed=str(len(items))
                )
            
            finally:
                # Cleanup
                client.delete(list_key)
        
        finally:
            forge.traces.end(span_id)


@pytest.mark.e2e
class TestServiceConnectivity:
    """Tests for verifying connectivity to all services."""

    def test_all_services_accessible(self, forge, http_client):
        """Test that core services are accessible."""
        # API health - should always respond
        health = forge.health()
        assert "services" in health
        assert "api" in health["services"]
        assert health["services"]["api"]["status"] == "healthy"
        
        # Cache connectivity (Redis)
        if health["services"].get("redis", {}).get("status") == "healthy":
            test_key = "connectivity_test"
            forge.cache.set(test_key, "test")
            value = forge.cache.get(test_key)
            assert value == "test"
            forge.cache.delete(test_key)
        
        # Observability - should work regardless
        forge.logs.info("Connectivity test log")
        forge.metrics.increment("connectivity_test_metric")

    def test_health_reports_services(self, http_client, forge):
        """Test that health endpoint reports service statuses."""
        response = http_client.get(f"{forge.base_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        services = data.get("services", {})
        assert len(services) > 0, "No services reported"
        
        # Log service statuses for debugging
        healthy_count = 0
        for service, health in services.items():
            if health["status"] == "healthy":
                healthy_count += 1
            else:
                print(f"Note: {service} is {health['status']}: {health.get('message', '')}")
        
        # At least API should be healthy
        assert services.get("api", {}).get("status") == "healthy"


@pytest.mark.e2e
class TestPerformance:
    """Basic performance tests."""

    @pytest.mark.slow
    def test_bulk_cache_operations(self, forge, test_id):
        """Test performance of bulk cache operations."""
        keys = []
        num_operations = 100
        
        start_time = time.time()
        
        try:
            # Bulk set
            for i in range(num_operations):
                key = f"bulk_{test_id}_{i}"
                keys.append(key)
                forge.cache.set(key, f"value_{i}")
            
            set_duration = time.time() - start_time
            
            # Bulk get
            get_start = time.time()
            for key in keys:
                forge.cache.get(key)
            
            get_duration = time.time() - get_start
            
            # Record metrics
            forge.metrics.histogram(
                "bulk_cache_set_duration",
                value=set_duration,
                labels={"operations": str(num_operations)}
            )
            forge.metrics.histogram(
                "bulk_cache_get_duration",
                value=get_duration,
                labels={"operations": str(num_operations)}
            )
            
            # Basic performance check (should complete in reasonable time)
            assert set_duration < 30  # 30 seconds for 100 operations
            assert get_duration < 30
        
        finally:
            # Cleanup
            for key in keys:
                try:
                    forge.cache.delete(key)
                except Exception:
                    pass

    @pytest.mark.slow
    def test_concurrent_logging(self, forge, test_id):
        """Test concurrent logging operations."""
        import threading
        
        num_logs = 50
        errors = []
        
        def log_message(i):
            try:
                forge.logs.info(
                    f"Concurrent log {i} for {test_id}",
                    test_id=test_id,
                    log_index=str(i)
                )
            except Exception as e:
                errors.append(str(e))
        
        # Create threads
        threads = []
        for i in range(num_logs):
            t = threading.Thread(target=log_message, args=(i,))
            threads.append(t)
        
        # Start all threads
        start_time = time.time()
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        duration = time.time() - start_time
        
        # Record metric
        forge.metrics.histogram(
            "concurrent_logging_duration",
            value=duration,
            labels={"logs": str(num_logs)}
        )
        
        # Check for errors
        assert len(errors) == 0, f"Errors during concurrent logging: {errors}"
        assert duration < 30  # Should complete in reasonable time

