# 🔥 Forge

**Self-hosted infrastructure for startups. Stop wasting time on setup.**

Forge gives you production-ready databases, caching, and observability in one command.

## Quick Start

```bash
# Start everything
make start

# Check health
make health
```

That's it. You now have:
- **MySQL** at `localhost:3306`
- **Redis** at `localhost:6379`
- **Grafana** at `localhost/services/grafana`
- **Prometheus** metrics
- **Loki** logs
- **Tempo** traces

## Python SDK

```bash
pip install forge-sdk
```

```python
from forge import Forge

f = Forge("localhost")

# Database
result = f.db.query("SELECT * FROM users")
engine = f.db.engine()  # SQLAlchemy engine

# Cache
f.cache.set("key", "value", ttl=3600)
value = f.cache.get("key")
redis = f.cache.client()  # Redis client

# Observability
f.logs.info("User logged in", user_id=123)
f.metrics.increment("requests_total")

# System
print(f.info())
```

## URLs

| Path | Description |
|------|-------------|
| `localhost/` | Dashboard (coming soon) |
| `localhost/docs` | API documentation |
| `localhost/api/v1/*` | REST API |
| `localhost/services/grafana` | Grafana dashboards |
| `localhost/services/prometheus` | Prometheus UI |

## Configuration

Edit `config.yaml`:

```yaml
services:
  db:
    mysql:
      enabled: true
      port: 3306
  cache:
    redis:
      enabled: true
  grafana:
    enabled: true
```

Then restart: `make restart`

## Commands

| Command | Description |
|---------|-------------|
| `make start` | Start all services |
| `make stop` | Stop all services |
| `make health` | Check service health |
| `make logs` | View logs |
| `make clean` | Remove everything |

## License

MIT
