package handlers

import (
	"context"
	"encoding/json"
	"net/http"

	"connectrpc.com/connect"
	forgev1 "github.com/forge/api/gen/forge/v1"
	"github.com/forge/api/internal/observe"
)

type ObserveHandler struct {
	lokiClient *observe.LokiClient
}

func NewObserveHandler(loki *observe.LokiClient) *ObserveHandler {
	return &ObserveHandler{
		lokiClient: loki,
	}
}

func (h *ObserveHandler) Log(
	ctx context.Context,
	req *connect.Request[forgev1.LogRequest],
) (*connect.Response[forgev1.LogResponse], error) {
	err := h.lokiClient.Push(ctx, req.Msg.Level, req.Msg.Message, req.Msg.Labels)
	if err != nil {
		return nil, connect.NewError(connect.CodeInternal, err)
	}
	
	return connect.NewResponse(&forgev1.LogResponse{
		Ok: true,
	}), nil
}

func (h *ObserveHandler) Metric(
	ctx context.Context,
	req *connect.Request[forgev1.MetricRequest],
) (*connect.Response[forgev1.MetricResponse], error) {
	// For now, metrics are collected via Prometheus scraping
	// This endpoint can be used for push-based metrics in the future
	return connect.NewResponse(&forgev1.MetricResponse{
		Ok: true,
	}), nil
}

func (h *ObserveHandler) Trace(
	ctx context.Context,
	req *connect.Request[forgev1.TraceRequest],
) (*connect.Response[forgev1.TraceResponse], error) {
	// TODO: Implement trace pushing to Tempo
	return connect.NewResponse(&forgev1.TraceResponse{
		Ok:      true,
		TraceId: req.Msg.TraceId,
		SpanId:  req.Msg.SpanId,
	}), nil
}

// REST handlers
func LogsREST(h *ObserveHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		
		var req forgev1.LogRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		
		resp, err := h.Log(r.Context(), connect.NewRequest(&req))
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp.Msg)
	}
}

func MetricsREST(h *ObserveHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		
		var req forgev1.MetricRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		
		resp, err := h.Metric(r.Context(), connect.NewRequest(&req))
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp.Msg)
	}
}

func TracesREST(h *ObserveHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		
		var req forgev1.TraceRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		
		resp, err := h.Trace(r.Context(), connect.NewRequest(&req))
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp.Msg)
	}
}

