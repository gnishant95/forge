package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"connectrpc.com/connect"
	forgev1 "github.com/forge/api/gen/forge/v1"
	"github.com/forge/api/internal/cache"
	"github.com/forge/api/internal/db"
)

type ForgeHandler struct {
	startTime   time.Time
	mysqlClient *db.MySQLClient
	redisClient *cache.RedisClient
}

func NewForgeHandler(startTime time.Time, mysql *db.MySQLClient, redis *cache.RedisClient) *ForgeHandler {
	return &ForgeHandler{
		startTime:   startTime,
		mysqlClient: mysql,
		redisClient: redis,
	}
}

// ServiceHealth represents the health of a single service
type ServiceHealth struct {
	Status  string `json:"status"`  // "healthy", "unhealthy", "unknown"
	Message string `json:"message,omitempty"`
}

// HealthResponse represents the full health check response
type HealthCheckResponse struct {
	OK       bool                      `json:"ok"`
	Uptime   string                    `json:"uptime"`
	Services map[string]*ServiceHealth `json:"services"`
}

func (h *ForgeHandler) Health(
	ctx context.Context,
	req *connect.Request[forgev1.HealthRequest],
) (*connect.Response[forgev1.HealthResponse], error) {
	return connect.NewResponse(&forgev1.HealthResponse{
		Ok: true,
	}), nil
}

func (h *ForgeHandler) Info(
	ctx context.Context,
	req *connect.Request[forgev1.InfoRequest],
) (*connect.Response[forgev1.InfoResponse], error) {
	// Deprecated - keeping for proto compatibility
	return connect.NewResponse(&forgev1.InfoResponse{
		Version: "0.1.0",
		Uptime:  time.Since(h.startTime).String(),
	}), nil
}

// checkServiceHealth checks health of external services via HTTP
func checkHTTPHealth(url string, timeout time.Duration) *ServiceHealth {
	client := &http.Client{Timeout: timeout}
	resp, err := client.Get(url)
	if err != nil {
		return &ServiceHealth{Status: "unhealthy", Message: err.Error()}
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return &ServiceHealth{Status: "healthy"}
	}
	return &ServiceHealth{Status: "unhealthy", Message: resp.Status}
}

// HealthREST returns detailed health of all services
func HealthREST(h *ForgeHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		timeout := 2 * time.Second

		services := make(map[string]*ServiceHealth)
		allHealthy := true

		// API (self)
		services["api"] = &ServiceHealth{Status: "healthy"}

		// MySQL
		if h.mysqlClient != nil {
			if err := h.mysqlClient.Ping(ctx); err == nil {
				services["mysql"] = &ServiceHealth{Status: "healthy"}
			} else {
				services["mysql"] = &ServiceHealth{Status: "unhealthy", Message: err.Error()}
				allHealthy = false
			}
		} else {
			services["mysql"] = &ServiceHealth{Status: "unhealthy", Message: "not configured"}
			allHealthy = false
		}

		// Redis
		if h.redisClient != nil {
			if err := h.redisClient.Ping(ctx); err == nil {
				services["redis"] = &ServiceHealth{Status: "healthy"}
			} else {
				services["redis"] = &ServiceHealth{Status: "unhealthy", Message: err.Error()}
				allHealthy = false
			}
		} else {
			services["redis"] = &ServiceHealth{Status: "unhealthy", Message: "not configured"}
			allHealthy = false
		}

		// Grafana
		services["grafana"] = checkHTTPHealth("http://grafana:3000/api/health", timeout)
		if services["grafana"].Status != "healthy" {
			allHealthy = false
		}

		// Prometheus
		services["prometheus"] = checkHTTPHealth("http://prometheus:9090/-/ready", timeout)
		if services["prometheus"].Status != "healthy" {
			allHealthy = false
		}

		// Loki
		services["loki"] = checkHTTPHealth("http://loki:3100/ready", timeout)
		if services["loki"].Status != "healthy" {
			allHealthy = false
		}

		// Tempo
		services["tempo"] = checkHTTPHealth("http://tempo:3200/ready", timeout)
		if services["tempo"].Status != "healthy" {
			allHealthy = false
		}

		// Nginx (check via localhost since it's the entry point)
		services["nginx"] = checkHTTPHealth("http://nginx:80/", timeout)
		if services["nginx"].Status != "healthy" {
			allHealthy = false
		}

		response := HealthCheckResponse{
			OK:       allHealthy,
			Uptime:   time.Since(h.startTime).Round(time.Second).String(),
			Services: services,
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}
}
