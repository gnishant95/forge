package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"github.com/forge/api/internal/logsources"
)

// maxRequestBodySize is the maximum allowed size for request bodies (1MB)
const maxRequestBodySize = 1 << 20

// LogSourcesHandler handles log source management requests
type LogSourcesHandler struct {
	manager *logsources.Manager
}

// NewLogSourcesHandler creates a new log sources handler
func NewLogSourcesHandler(manager *logsources.Manager) *LogSourcesHandler {
	return &LogSourcesHandler{manager: manager}
}

// HandleLogSources handles /api/v1/logs/sources requests
func (h *LogSourcesHandler) HandleLogSources(w http.ResponseWriter, r *http.Request) {
	// Extract source name from path if present
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/logs/sources")
	path = strings.TrimPrefix(path, "/")

	switch r.Method {
	case "GET":
		if path == "" || path == "reload" {
			h.listSources(w, r)
		} else {
			h.getSource(w, r, path)
		}
	case "POST":
		if path == "reload" {
			h.reloadPromtail(w, r)
		} else {
			h.addSource(w, r)
		}
	case "DELETE":
		if path != "" {
			h.deleteSource(w, r, path)
		} else {
			http.Error(w, "Source name required", http.StatusBadRequest)
		}
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// listSources returns all configured log sources
func (h *LogSourcesHandler) listSources(w http.ResponseWriter, r *http.Request) {
	sources := h.manager.List()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"sources": sources,
		"count":   len(sources),
	})
}

// getSource returns a specific log source
func (h *LogSourcesHandler) getSource(w http.ResponseWriter, r *http.Request, name string) {
	source, found := h.manager.Get(name)
	if !found {
		http.Error(w, "Source not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(source)
}

// addSource adds a new log source
func (h *LogSourcesHandler) addSource(w http.ResponseWriter, r *http.Request) {
	// Limit request body size to prevent oversized payloads
	r.Body = http.MaxBytesReader(w, r.Body, maxRequestBodySize)

	var source logsources.LogSource
	if err := json.NewDecoder(r.Body).Decode(&source); err != nil {
		var maxBytesErr *http.MaxBytesError
		if errors.As(err, &maxBytesErr) {
			http.Error(w, "Request body too large", http.StatusRequestEntityTooLarge)
			return
		}
		http.Error(w, "Invalid JSON: "+err.Error(), http.StatusBadRequest)
		return
	}

	// Validate
	if source.Name == "" {
		http.Error(w, "name is required", http.StatusBadRequest)
		return
	}
	if source.Path == "" {
		http.Error(w, "path is required", http.StatusBadRequest)
		return
	}

	// Add source
	if err := h.manager.Add(source); err != nil {
		http.Error(w, "Failed to add source: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Reload Promtail
	if err := h.manager.ReloadPromtail(); err != nil {
		// Log but don't fail - config is saved, just needs manual reload
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"ok":      true,
			"source":  source,
			"warning": "Config saved but Promtail reload failed: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]any{
		"ok":     true,
		"source": source,
	})
}

// deleteSource removes a log source
func (h *LogSourcesHandler) deleteSource(w http.ResponseWriter, r *http.Request, name string) {
	if err := h.manager.Delete(name); err != nil {
		if strings.Contains(err.Error(), "not found") {
			http.Error(w, err.Error(), http.StatusNotFound)
		} else {
			http.Error(w, "Failed to delete source: "+err.Error(), http.StatusInternalServerError)
		}
		return
	}

	// Reload Promtail
	reloadErr := h.manager.ReloadPromtail()

	w.Header().Set("Content-Type", "application/json")
	response := map[string]any{"ok": true, "deleted": name}
	if reloadErr != nil {
		response["warning"] = "Promtail reload failed: " + reloadErr.Error()
	}
	json.NewEncoder(w).Encode(response)
}

// reloadPromtail forces a Promtail config reload
func (h *LogSourcesHandler) reloadPromtail(w http.ResponseWriter, r *http.Request) {
	if err := h.manager.ReloadPromtail(); err != nil {
		http.Error(w, "Reload failed: "+err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]bool{"ok": true})
}
