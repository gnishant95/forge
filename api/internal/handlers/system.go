package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/forge/api/internal/logger"
	"github.com/forge/api/internal/system"
)

// SystemHandler handles system information requests
type SystemHandler struct {
	docker *system.DockerClient
}

// NewSystemHandler creates a new system handler
func NewSystemHandler() *SystemHandler {
	return &SystemHandler{
		docker: system.NewDockerClient(),
	}
}

// GetSystemInfo returns detailed system and container information
func (h *SystemHandler) GetSystemInfo(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	info, err := h.docker.GetSystemInfo(r.Context())
	if err != nil {
		logger.Error("Failed to get system info", err)
		http.Error(w, "Failed to get system info", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(info)
}
