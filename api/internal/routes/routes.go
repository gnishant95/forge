// Package routes manages dynamic nginx routes
package routes

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"

	"gopkg.in/yaml.v3"
)

// Route represents a dynamic nginx route
type Route struct {
	Name        string `json:"name" yaml:"name"`
	Path        string `json:"path" yaml:"path"`               // e.g., "/myapp/"
	Target      string `json:"target" yaml:"target"`           // e.g., "http://service:8000" or "https://api.example.com"
	StripPrefix bool   `json:"strip_prefix" yaml:"strip_prefix"` // Remove path prefix before forwarding
}

// RoutesConfig is the persisted routes file structure
type RoutesConfig struct {
	Routes []Route `yaml:"routes"`
}

// Manager handles route storage and nginx configuration
type Manager struct {
	mu         sync.RWMutex
	routes     map[string]Route
	configPath string // Path to routes.yaml
	nginxConf  string // Path to generated nginx routes config
}

// NewManager creates a new route manager
func NewManager(configPath, nginxConfPath string) (*Manager, error) {
	m := &Manager{
		routes:     make(map[string]Route),
		configPath: configPath,
		nginxConf:  nginxConfPath,
	}

	// Load existing routes
	if err := m.load(); err != nil && !os.IsNotExist(err) {
		return nil, err
	}

	return m, nil
}

// List returns all routes
func (m *Manager) List() []Route {
	m.mu.RLock()
	defer m.mu.RUnlock()

	routes := make([]Route, 0, len(m.routes))
	for _, r := range m.routes {
		routes = append(routes, r)
	}
	return routes
}

// Get returns a route by name
func (m *Manager) Get(name string) (Route, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	r, ok := m.routes[name]
	return r, ok
}

// Add creates or updates a route
func (m *Manager) Add(route Route) error {
	// Validate
	if route.Name == "" {
		return fmt.Errorf("route name is required")
	}
	if route.Path == "" {
		return fmt.Errorf("route path is required")
	}
	if route.Target == "" {
		return fmt.Errorf("route target is required")
	}

	// Ensure path starts with / and ends with /
	if !strings.HasPrefix(route.Path, "/") {
		route.Path = "/" + route.Path
	}
	if !strings.HasSuffix(route.Path, "/") {
		route.Path = route.Path + "/"
	}

	m.mu.Lock()
	m.routes[route.Name] = route
	m.mu.Unlock()

	// Save and regenerate nginx config
	if err := m.save(); err != nil {
		return err
	}

	return m.regenerateNginx()
}

// Remove deletes a route
func (m *Manager) Remove(name string) error {
	m.mu.Lock()
	if _, ok := m.routes[name]; !ok {
		m.mu.Unlock()
		return fmt.Errorf("route not found: %s", name)
	}
	delete(m.routes, name)
	m.mu.Unlock()

	if err := m.save(); err != nil {
		return err
	}

	return m.regenerateNginx()
}

// Reload sends reload signal to nginx
func (m *Manager) Reload() error {
	cmd := exec.Command("docker", "exec", "forge-nginx", "nginx", "-s", "reload")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("nginx reload failed: %s - %v", string(output), err)
	}
	return nil
}

// load reads routes from config file
func (m *Manager) load() error {
	data, err := os.ReadFile(m.configPath)
	if err != nil {
		return err
	}

	var cfg RoutesConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return err
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	for _, r := range cfg.Routes {
		m.routes[r.Name] = r
	}

	return nil
}

// save writes routes to config file
func (m *Manager) save() error {
	m.mu.RLock()
	routes := make([]Route, 0, len(m.routes))
	for _, r := range m.routes {
		routes = append(routes, r)
	}
	m.mu.RUnlock()

	cfg := RoutesConfig{Routes: routes}
	data, err := yaml.Marshal(&cfg)
	if err != nil {
		return err
	}

	// Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(m.configPath), 0755); err != nil {
		return err
	}

	return os.WriteFile(m.configPath, data, 0644)
}

// regenerateNginx creates nginx config and reloads
func (m *Manager) regenerateNginx() error {
	m.mu.RLock()
	routes := make([]Route, 0, len(m.routes))
	for _, r := range m.routes {
		routes = append(routes, r)
	}
	m.mu.RUnlock()

	// Generate nginx config
	config := m.generateNginxConfig(routes)

	// Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(m.nginxConf), 0755); err != nil {
		return err
	}

	// Write config
	if err := os.WriteFile(m.nginxConf, []byte(config), 0644); err != nil {
		return err
	}

	// Reload nginx
	return m.Reload()
}

// generateNginxConfig creates nginx location blocks for routes
func (m *Manager) generateNginxConfig(routes []Route) string {
	var sb strings.Builder

	sb.WriteString("# Dynamic routes - auto-generated, do not edit\n")
	sb.WriteString("# Managed by Forge API\n\n")

	for _, r := range routes {
		sb.WriteString(fmt.Sprintf("# Route: %s\n", r.Name))
		sb.WriteString(fmt.Sprintf("location %s {\n", r.Path))

		if r.StripPrefix {
			// Strip the path prefix (add trailing slash to target)
			target := r.Target
			if !strings.HasSuffix(target, "/") {
				target = target + "/"
			}
			sb.WriteString(fmt.Sprintf("    proxy_pass %s;\n", target))
		} else {
			// Keep the path (no trailing slash)
			target := strings.TrimSuffix(r.Target, "/")
			sb.WriteString(fmt.Sprintf("    proxy_pass %s;\n", target))
		}

		sb.WriteString("    proxy_http_version 1.1;\n")
		sb.WriteString("    proxy_set_header Host $host;\n")
		sb.WriteString("    proxy_set_header X-Real-IP $remote_addr;\n")
		sb.WriteString("    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n")
		sb.WriteString("    proxy_set_header X-Forwarded-Proto $scheme;\n")
		sb.WriteString("    proxy_set_header Upgrade $http_upgrade;\n")
		sb.WriteString("    proxy_set_header Connection \"upgrade\";\n")
		sb.WriteString("}\n\n")
	}

	return sb.String()
}

