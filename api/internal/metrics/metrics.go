// Package metrics provides Prometheus metrics instrumentation for Forge API
//
// Metrics exposed:
//   - forge_http_requests_total (counter) - Total HTTP requests by endpoint, method, status
//   - forge_http_request_duration_seconds (histogram) - Request latency by endpoint, method
//   - forge_http_requests_in_flight (gauge) - Current in-flight requests
package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// HTTPRequestsTotal counts total HTTP requests
	HTTPRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "forge_http_requests_total",
			Help: "Total number of HTTP requests by endpoint, method, and status code",
		},
		[]string{"endpoint", "method", "status"},
	)

	// HTTPRequestDuration measures request latency
	HTTPRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "forge_http_request_duration_seconds",
			Help:    "HTTP request latency in seconds",
			Buckets: []float64{.001, .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10},
		},
		[]string{"endpoint", "method"},
	)

	// HTTPRequestsInFlight tracks current in-flight requests
	HTTPRequestsInFlight = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "forge_http_requests_in_flight",
			Help: "Current number of HTTP requests being processed",
		},
	)

	// DBQueryDuration measures database query latency
	DBQueryDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "forge_db_query_duration_seconds",
			Help:    "Database query latency in seconds",
			Buckets: []float64{.001, .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5},
		},
		[]string{"db", "operation"},
	)

	// CacheOperationDuration measures cache operation latency
	CacheOperationDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "forge_cache_operation_duration_seconds",
			Help:    "Cache operation latency in seconds",
			Buckets: []float64{.0001, .0005, .001, .005, .01, .025, .05, .1},
		},
		[]string{"operation"},
	)

	// ServiceUp tracks service health (1 = up, 0 = down)
	ServiceUp = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "forge_service_up",
			Help: "Service health status (1 = up, 0 = down)",
		},
		[]string{"service"},
	)
)

// RecordRequest records metrics for an HTTP request
func RecordRequest(endpoint, method, status string, durationSeconds float64) {
	HTTPRequestsTotal.WithLabelValues(endpoint, method, status).Inc()
	HTTPRequestDuration.WithLabelValues(endpoint, method).Observe(durationSeconds)
}

// RecordDBQuery records metrics for a database query
func RecordDBQuery(db, operation string, durationSeconds float64) {
	DBQueryDuration.WithLabelValues(db, operation).Observe(durationSeconds)
}

// RecordCacheOperation records metrics for a cache operation
func RecordCacheOperation(operation string, durationSeconds float64) {
	CacheOperationDuration.WithLabelValues(operation).Observe(durationSeconds)
}

// SetServiceUp sets the health status of a service
func SetServiceUp(service string, up bool) {
	val := 0.0
	if up {
		val = 1.0
	}
	ServiceUp.WithLabelValues(service).Set(val)
}

