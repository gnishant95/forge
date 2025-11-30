package handlers

import (
	"encoding/json"
	"net/http"
	"strings"

	"github.com/forge/api/internal/routes"
)

// RoutesHandler handles route management API
type RoutesHandler struct {
	manager *routes.Manager
}

// NewRoutesHandler creates a new routes handler
func NewRoutesHandler(manager *routes.Manager) *RoutesHandler {
	return &RoutesHandler{manager: manager}
}

// ListRoutes returns all dynamic routes
func (h *RoutesHandler) ListRoutes(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	routes := h.manager.List()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"routes": routes,
		"count":  len(routes),
	})
}

// AddRoute creates or updates a route
func (h *RoutesHandler) AddRoute(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var route routes.Route
	if err := json.NewDecoder(r.Body).Decode(&route); err != nil {
		http.Error(w, "Invalid JSON: "+err.Error(), http.StatusBadRequest)
		return
	}

	if err := h.manager.Add(route); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"ok":      true,
		"message": "Route added and nginx reloaded",
		"route":   route,
	})
}

// DeleteRoute removes a route
func (h *RoutesHandler) DeleteRoute(w http.ResponseWriter, r *http.Request) {
	if r.Method != "DELETE" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract route name from path: /api/v1/routes/{name}
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/routes/")
	name := strings.TrimSuffix(path, "/")

	if name == "" {
		http.Error(w, "Route name is required", http.StatusBadRequest)
		return
	}

	if err := h.manager.Remove(name); err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"ok":      true,
		"message": "Route deleted and nginx reloaded",
	})
}

// ReloadNginx forces nginx reload
func (h *RoutesHandler) ReloadNginx(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	if err := h.manager.Reload(); err != nil {
		http.Error(w, "Reload failed: "+err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"ok":      true,
		"message": "nginx reloaded",
	})
}

// HandleRoutes is the main handler that routes to sub-handlers
func (h *RoutesHandler) HandleRoutes(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/routes")

	switch {
	case path == "" || path == "/":
		// /api/v1/routes
		switch r.Method {
		case "GET":
			h.ListRoutes(w, r)
		case "POST":
			h.AddRoute(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}

	case path == "/reload":
		// /api/v1/routes/reload
		h.ReloadNginx(w, r)

	default:
		// /api/v1/routes/{name}
		if r.Method == "DELETE" {
			h.DeleteRoute(w, r)
		} else if r.Method == "GET" {
			// Get single route
			name := strings.TrimPrefix(path, "/")
			name = strings.TrimSuffix(name, "/")
			route, ok := h.manager.Get(name)
			if !ok {
				http.Error(w, "Route not found", http.StatusNotFound)
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(route)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	}
}

