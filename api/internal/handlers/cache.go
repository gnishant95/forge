package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"os"
	"strings"
	"time"

	"connectrpc.com/connect"
	forgev1 "github.com/forge/api/gen/forge/v1"
	"github.com/forge/api/internal/cache"
)

type CacheHandler struct {
	redisClient *cache.RedisClient
}

func NewCacheHandler(redis *cache.RedisClient) *CacheHandler {
	return &CacheHandler{
		redisClient: redis,
	}
}

func (h *CacheHandler) Get(
	ctx context.Context,
	req *connect.Request[forgev1.GetRequest],
) (*connect.Response[forgev1.GetResponse], error) {
	if h.redisClient == nil {
		return nil, connect.NewError(connect.CodeUnavailable, nil)
	}
	
	value, found, err := h.redisClient.Get(ctx, req.Msg.Key)
	if err != nil {
		return nil, connect.NewError(connect.CodeInternal, err)
	}
	
	return connect.NewResponse(&forgev1.GetResponse{
		Value: value,
		Found: found,
	}), nil
}

func (h *CacheHandler) Set(
	ctx context.Context,
	req *connect.Request[forgev1.SetRequest],
) (*connect.Response[forgev1.SetResponse], error) {
	if h.redisClient == nil {
		return nil, connect.NewError(connect.CodeUnavailable, nil)
	}
	
	ttl := time.Duration(req.Msg.TtlSeconds) * time.Second
	err := h.redisClient.Set(ctx, req.Msg.Key, req.Msg.Value, ttl)
	if err != nil {
		return nil, connect.NewError(connect.CodeInternal, err)
	}
	
	return connect.NewResponse(&forgev1.SetResponse{
		Ok: true,
	}), nil
}

func (h *CacheHandler) Delete(
	ctx context.Context,
	req *connect.Request[forgev1.DeleteRequest],
) (*connect.Response[forgev1.DeleteResponse], error) {
	if h.redisClient == nil {
		return nil, connect.NewError(connect.CodeUnavailable, nil)
	}
	
	deleted, err := h.redisClient.Delete(ctx, req.Msg.Key)
	if err != nil {
		return nil, connect.NewError(connect.CodeInternal, err)
	}
	
	return connect.NewResponse(&forgev1.DeleteResponse{
		Deleted: deleted,
	}), nil
}

func (h *CacheHandler) GetInfo(
	ctx context.Context,
	req *connect.Request[forgev1.CacheInfoRequest],
) (*connect.Response[forgev1.CacheInfoResponse], error) {
	host := os.Getenv("REDIS_HOST")
	if host == "" {
		host = "localhost"
	}
	port := os.Getenv("REDIS_PORT")
	if port == "" {
		port = "6379"
	}
	externalHost := os.Getenv("EXTERNAL_HOST")
	if externalHost == "" {
		externalHost = "localhost"
	}
	
	return connect.NewResponse(&forgev1.CacheInfoResponse{
		Host:     externalHost,
		Port:     6379,
		Password: "",
		Url:      "redis://" + externalHost + ":" + port,
	}), nil
}

// REST handlers
func CacheREST(h *CacheHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Extract key from path: /api/v1/cache/{key}
		path := strings.TrimPrefix(r.URL.Path, "/api/v1/cache/")
		if path == "" || path == "info" {
			return // Let other handlers handle these
		}
		
		key := path
		ctx := r.Context()
		
		switch r.Method {
		case "GET":
			resp, err := h.Get(ctx, connect.NewRequest(&forgev1.GetRequest{Key: key}))
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(resp.Msg)
			
		case "POST", "PUT":
			var body struct {
				Value string `json:"value"`
				TTL   int64  `json:"ttl"`
			}
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
			resp, err := h.Set(ctx, connect.NewRequest(&forgev1.SetRequest{
				Key:        key,
				Value:      body.Value,
				TtlSeconds: body.TTL,
			}))
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(resp.Msg)
			
		case "DELETE":
			resp, err := h.Delete(ctx, connect.NewRequest(&forgev1.DeleteRequest{Key: key}))
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(resp.Msg)
			
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	}
}

func CacheInfoREST(h *CacheHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		resp, err := h.GetInfo(r.Context(), connect.NewRequest(&forgev1.CacheInfoRequest{}))
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp.Msg)
	}
}

