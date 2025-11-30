package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"connectrpc.com/connect"
	forgev1 "github.com/forge/api/gen/forge/v1"
	"github.com/forge/api/internal/db"
	"github.com/forge/api/internal/cache"
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
	uptime := time.Since(h.startTime)
	
	services := make(map[string]*forgev1.ServiceStatus)
	
	// MySQL status
	if h.mysqlClient != nil {
		if err := h.mysqlClient.Ping(ctx); err == nil {
			services["mysql"] = &forgev1.ServiceStatus{
				Status:  "running",
				Message: "Connected",
			}
		} else {
			services["mysql"] = &forgev1.ServiceStatus{
				Status:  "error",
				Message: err.Error(),
			}
		}
	} else {
		services["mysql"] = &forgev1.ServiceStatus{
			Status:  "stopped",
			Message: "Not configured",
		}
	}
	
	// Redis status
	if h.redisClient != nil {
		if err := h.redisClient.Ping(ctx); err == nil {
			services["redis"] = &forgev1.ServiceStatus{
				Status:  "running",
				Message: "Connected",
			}
		} else {
			services["redis"] = &forgev1.ServiceStatus{
				Status:  "error",
				Message: err.Error(),
			}
		}
	} else {
		services["redis"] = &forgev1.ServiceStatus{
			Status:  "stopped",
			Message: "Not configured",
		}
	}
	
	return connect.NewResponse(&forgev1.InfoResponse{
		Version:  "0.1.0",
		Uptime:   uptime.String(),
		Services: services,
	}), nil
}

// REST handlers
func HealthREST(h *ForgeHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]bool{"ok": true})
	}
}

func InfoREST(h *ForgeHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		resp, _ := h.Info(ctx, connect.NewRequest(&forgev1.InfoRequest{}))
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp.Msg)
	}
}

