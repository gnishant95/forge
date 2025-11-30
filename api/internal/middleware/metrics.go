// Package middleware provides HTTP middleware for Forge API
package middleware

import (
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/forge/api/internal/logger"
	"github.com/forge/api/internal/metrics"
)

// responseWriter wraps http.ResponseWriter to capture status code
type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

// Metrics wraps an http.Handler with Prometheus metrics and structured logging
func Metrics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Track in-flight requests
		metrics.HTTPRequestsInFlight.Inc()
		defer metrics.HTTPRequestsInFlight.Dec()

		// Wrap response writer to capture status
		rw := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

		// Call the next handler
		next.ServeHTTP(rw, r)

		// Calculate duration
		duration := time.Since(start)

		// Normalize endpoint for metrics (remove IDs, query params)
		endpoint := normalizeEndpoint(r.URL.Path)

		// Record metrics
		metrics.RecordRequest(
			endpoint,
			r.Method,
			strconv.Itoa(rw.statusCode),
			duration.Seconds(),
		)

		// Log request (skip health checks and metrics to reduce noise)
		if !isHealthOrMetrics(r.URL.Path) {
			logger.RequestLog(r.Method, r.URL.Path, rw.statusCode, duration, nil)
		}
	})
}

// normalizeEndpoint normalizes URL paths for metrics labels
// Replaces dynamic segments like IDs with placeholders
func normalizeEndpoint(path string) string {
	// Remove query string
	if idx := strings.Index(path, "?"); idx != -1 {
		path = path[:idx]
	}

	// Common patterns to normalize
	parts := strings.Split(path, "/")
	for i, part := range parts {
		// Replace UUIDs
		if len(part) == 36 && strings.Count(part, "-") == 4 {
			parts[i] = ":id"
			continue
		}
		// Replace numeric IDs
		if _, err := strconv.Atoi(part); err == nil && len(part) > 0 {
			parts[i] = ":id"
			continue
		}
	}

	return strings.Join(parts, "/")
}

// isHealthOrMetrics checks if path is health or metrics endpoint
func isHealthOrMetrics(path string) bool {
	return path == "/health" ||
		path == "/api/v1/health" ||
		path == "/metrics" ||
		path == "/api/v1/metrics"
}

