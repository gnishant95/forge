# Forge SDK

Python SDK for the Forge self-hosted infrastructure platform.

## Installation

```bash
pip install forge-sdk

# With SQLAlchemy support
pip install forge-sdk[sqlalchemy]

# With Redis client support
pip install forge-sdk[redis]

# With everything
pip install forge-sdk[all]
```

## Quick Start

```python
from forge import Forge

# Connect to Forge
f = Forge("localhost")

# Check health
print(f.health())  # {"ok": True}

# Get system info
print(f.info())
```

## Database

```python
# Simple queries
result = f.db.query("SELECT * FROM users")
print(result["rows"])

# Execute statements
f.db.execute("INSERT INTO users (name) VALUES (%s)", ["Alice"])

# SQLAlchemy integration
engine = f.db.engine()
engine = f.db.engine(database="mydb")

# Get connection URL
url = f.db.url()  # mysql+pymysql://user:pass@host:port
```

## Cache

```python
# Set/Get values
f.cache.set("session:123", "user_data", ttl=3600)
value = f.cache.get("session:123")
f.cache.delete("session:123")

# Redis client
redis = f.cache.client()
redis.hset("user:1", "name", "Alice")
```

## Observability

### Logs

```python
f.logs.info("User logged in", user_id=123)
f.logs.error("Payment failed", order_id=456, error="timeout")
f.logs.debug("Processing request", path="/api/users")
```

### Metrics

```python
f.metrics.increment("requests_total", labels={"path": "/api"})
f.metrics.gauge("active_users", 42)
f.metrics.histogram("response_time", 0.234)
```

### Traces

```python
span_id = f.traces.start("process_order", attributes={"order_id": "123"})
# ... do work ...
f.traces.end(span_id)
```

## Configuration

```python
# Default (localhost:80)
f = Forge()

# Custom host
f = Forge("myserver.com")

# Custom port
f = Forge("localhost", port=8080)

# With path prefix (for reverse proxy)
f = Forge("myserver.com/forge")
```

## License

MIT

