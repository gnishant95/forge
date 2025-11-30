package handlers

import (
	"net/http"
)

// SwaggerUI serves the Swagger UI
func SwaggerUI(w http.ResponseWriter, r *http.Request) {
	html := `<!DOCTYPE html>
<html>
<head>
    <title>Forge API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>
        body { margin: 0; padding: 0; }
        .swagger-ui .topbar { display: none; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({
            url: "/openapi.json",
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis],
            layout: "BaseLayout"
        });
    </script>
</body>
</html>`
	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(html))
}

// OpenAPISpec returns the OpenAPI specification
func OpenAPISpec(w http.ResponseWriter, r *http.Request) {
	spec := `{
  "openapi": "3.0.0",
  "info": {
    "title": "Forge API",
    "version": "0.1.0",
    "description": "Self-hosted infrastructure API"
  },
  "servers": [
    {"url": "/api/v1"}
  ],
  "paths": {
    "/health": {
      "get": {
        "summary": "Health check",
        "tags": ["System"],
        "responses": {
          "200": {
            "description": "Service is healthy",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "ok": {"type": "boolean"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/info": {
      "get": {
        "summary": "System information",
        "tags": ["System"],
        "responses": {
          "200": {
            "description": "System info",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "version": {"type": "string"},
                    "uptime": {"type": "string"},
                    "services": {"type": "object"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/db/query": {
      "post": {
        "summary": "Execute SQL query",
        "tags": ["Database"],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "sql": {"type": "string", "example": "SELECT * FROM users"},
                  "database": {"type": "string", "example": "mydb"},
                  "type": {"type": "string", "example": "mysql"}
                },
                "required": ["sql"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Query results",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "rows": {"type": "array"},
                    "columns": {"type": "array"},
                    "row_count": {"type": "integer"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/db/info": {
      "get": {
        "summary": "Get database connection info",
        "tags": ["Database"],
        "responses": {
          "200": {
            "description": "Connection info for SQLAlchemy",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                    "user": {"type": "string"},
                    "password": {"type": "string"},
                    "url": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/cache/{key}": {
      "get": {
        "summary": "Get cached value",
        "tags": ["Cache"],
        "parameters": [
          {"name": "key", "in": "path", "required": true, "schema": {"type": "string"}}
        ],
        "responses": {
          "200": {
            "description": "Cached value",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "value": {"type": "string"},
                    "found": {"type": "boolean"}
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "summary": "Set cached value",
        "tags": ["Cache"],
        "parameters": [
          {"name": "key", "in": "path", "required": true, "schema": {"type": "string"}}
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "value": {"type": "string"},
                  "ttl": {"type": "integer", "description": "TTL in seconds"}
                },
                "required": ["value"]
              }
            }
          }
        },
        "responses": {
          "200": {"description": "Value set"}
        }
      },
      "delete": {
        "summary": "Delete cached value",
        "tags": ["Cache"],
        "parameters": [
          {"name": "key", "in": "path", "required": true, "schema": {"type": "string"}}
        ],
        "responses": {
          "200": {"description": "Value deleted"}
        }
      }
    },
    "/cache/info": {
      "get": {
        "summary": "Get cache connection info",
        "tags": ["Cache"],
        "responses": {
          "200": {
            "description": "Connection info for Redis client",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                    "url": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/logs": {
      "post": {
        "summary": "Push log entry",
        "tags": ["Observability"],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "message": {"type": "string"},
                  "level": {"type": "string", "enum": ["debug", "info", "warn", "error"]},
                  "labels": {"type": "object"}
                },
                "required": ["message"]
              }
            }
          }
        },
        "responses": {
          "200": {"description": "Log pushed"}
        }
      }
    },
    "/metrics": {
      "post": {
        "summary": "Push metric",
        "tags": ["Observability"],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": {"type": "string"},
                  "value": {"type": "number"},
                  "type": {"type": "string", "enum": ["counter", "gauge", "histogram"]},
                  "labels": {"type": "object"}
                },
                "required": ["name", "value"]
              }
            }
          }
        },
        "responses": {
          "200": {"description": "Metric pushed"}
        }
      }
    },
    "/traces": {
      "post": {
        "summary": "Push trace span",
        "tags": ["Observability"],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": {"type": "string", "description": "Span name"},
                  "trace_id": {"type": "string", "description": "Trace ID (auto-generated if empty)"},
                  "span_id": {"type": "string", "description": "Span ID (auto-generated if empty)"},
                  "parent_span_id": {"type": "string", "description": "Parent span ID"},
                  "start_time_ms": {"type": "integer", "description": "Start time in milliseconds"},
                  "duration_ms": {"type": "integer", "description": "Duration in milliseconds"},
                  "attributes": {"type": "object", "description": "Span attributes"}
                },
                "required": ["name"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Trace pushed",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "ok": {"type": "boolean"},
                    "trace_id": {"type": "string"},
                    "span_id": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}`
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(spec))
}

