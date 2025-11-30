// Package system provides system and container monitoring
package system

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"strings"
	"time"
)

// ContainerStats holds stats for a single container
type ContainerStats struct {
	Name          string   `json:"name"`
	Status        string   `json:"status"`
	State         string   `json:"state"`
	CPUPercent    float64  `json:"cpu_percent"`
	MemoryMB      float64  `json:"memory_mb"`
	MemoryLimitMB float64  `json:"memory_limit_mb"`
	MemoryPercent float64  `json:"memory_percent"`
	NetworkRxMB   float64  `json:"network_rx_mb"`
	NetworkTxMB   float64  `json:"network_tx_mb"`
	Uptime        string   `json:"uptime"`
	Endpoints     []string `json:"endpoints"`
	Image         string   `json:"image"`
}

// SystemInfo holds overall system information
type SystemInfo struct {
	Timestamp       string                     `json:"timestamp"`
	Containers      map[string]*ContainerStats `json:"containers"`
	TotalContainers int                        `json:"total_containers"`
	RunningCount    int                        `json:"running_count"`
	Recommendations []string                   `json:"recommendations,omitempty"`
}

// DockerClient communicates with Docker via socket
type DockerClient struct {
	httpClient *http.Client
}

// NewDockerClient creates a Docker client using the Unix socket
func NewDockerClient() *DockerClient {
	return &DockerClient{
		httpClient: &http.Client{
			Transport: &http.Transport{
				DialContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
					return net.Dial("unix", "/var/run/docker.sock")
				},
			},
			Timeout: 10 * time.Second,
		},
	}
}

// dockerContainer represents Docker API container response
type dockerContainer struct {
	ID      string            `json:"Id"`
	Names   []string          `json:"Names"`
	Image   string            `json:"Image"`
	State   string            `json:"State"`
	Status  string            `json:"Status"`
	Created int64             `json:"Created"`
	Ports   []dockerPort      `json:"Ports"`
	Labels  map[string]string `json:"Labels"`
}

type dockerPort struct {
	IP          string `json:"IP"`
	PrivatePort int    `json:"PrivatePort"`
	PublicPort  int    `json:"PublicPort"`
	Type        string `json:"Type"`
}

// dockerStats represents Docker stats API response
type dockerStats struct {
	CPUStats struct {
		CPUUsage struct {
			TotalUsage uint64 `json:"total_usage"`
		} `json:"cpu_usage"`
		SystemCPUUsage uint64 `json:"system_cpu_usage"`
		OnlineCPUs     int    `json:"online_cpus"`
	} `json:"cpu_stats"`
	PreCPUStats struct {
		CPUUsage struct {
			TotalUsage uint64 `json:"total_usage"`
		} `json:"cpu_usage"`
		SystemCPUUsage uint64 `json:"system_cpu_usage"`
	} `json:"precpu_stats"`
	MemoryStats struct {
		Usage uint64 `json:"usage"`
		Limit uint64 `json:"limit"`
	} `json:"memory_stats"`
	Networks map[string]struct {
		RxBytes uint64 `json:"rx_bytes"`
		TxBytes uint64 `json:"tx_bytes"`
	} `json:"networks"`
}

// GetSystemInfo retrieves system and container information
func (c *DockerClient) GetSystemInfo(ctx context.Context) (*SystemInfo, error) {
	info := &SystemInfo{
		Timestamp:  time.Now().Format(time.RFC3339),
		Containers: make(map[string]*ContainerStats),
	}

	// Get list of containers (filter by forge- prefix)
	containers, err := c.listContainers(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to list containers: %w", err)
	}

	for _, container := range containers {
		// Skip containers with no names
		if len(container.Names) == 0 {
			continue
		}

		name := strings.TrimPrefix(container.Names[0], "/")

		// Only include forge containers
		if !strings.HasPrefix(name, "forge-") {
			continue
		}

		info.TotalContainers++

		stats := &ContainerStats{
			Name:   name,
			Status: container.Status,
			State:  container.State,
			Image:  container.Image,
		}

		// Build endpoints from ports
		for _, port := range container.Ports {
			if port.PublicPort > 0 {
				stats.Endpoints = append(stats.Endpoints, fmt.Sprintf("localhost:%d", port.PublicPort))
			}
		}

		// Calculate uptime from Created timestamp
		created := time.Unix(container.Created, 0)
		stats.Uptime = formatDuration(time.Since(created))

		// Get live stats if container is running
		if container.State == "running" {
			info.RunningCount++

			liveStats, err := c.getContainerStats(ctx, container.ID)
			if err == nil {
				// Calculate CPU percentage
				cpuDelta := float64(liveStats.CPUStats.CPUUsage.TotalUsage - liveStats.PreCPUStats.CPUUsage.TotalUsage)
				systemDelta := float64(liveStats.CPUStats.SystemCPUUsage - liveStats.PreCPUStats.SystemCPUUsage)
				if systemDelta > 0 && liveStats.CPUStats.OnlineCPUs > 0 {
					stats.CPUPercent = (cpuDelta / systemDelta) * float64(liveStats.CPUStats.OnlineCPUs) * 100
				}

				// Memory stats
				stats.MemoryMB = float64(liveStats.MemoryStats.Usage) / 1024 / 1024
				stats.MemoryLimitMB = float64(liveStats.MemoryStats.Limit) / 1024 / 1024
				if stats.MemoryLimitMB > 0 {
					stats.MemoryPercent = (stats.MemoryMB / stats.MemoryLimitMB) * 100
				}

				// Network stats
				for _, net := range liveStats.Networks {
					stats.NetworkRxMB += float64(net.RxBytes) / 1024 / 1024
					stats.NetworkTxMB += float64(net.TxBytes) / 1024 / 1024
				}
			}
		}

		info.Containers[name] = stats
	}

	// Generate recommendations
	info.Recommendations = c.generateRecommendations(info.Containers)

	return info, nil
}

func (c *DockerClient) listContainers(ctx context.Context) ([]dockerContainer, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", "http://docker/containers/json?all=true", nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var containers []dockerContainer
	if err := json.NewDecoder(resp.Body).Decode(&containers); err != nil {
		return nil, err
	}

	return containers, nil
}

func (c *DockerClient) getContainerStats(ctx context.Context, containerID string) (*dockerStats, error) {
	url := fmt.Sprintf("http://docker/containers/%s/stats?stream=false", containerID)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var stats dockerStats
	if err := json.NewDecoder(resp.Body).Decode(&stats); err != nil {
		return nil, err
	}

	return &stats, nil
}

func (c *DockerClient) generateRecommendations(containers map[string]*ContainerStats) []string {
	var recs []string

	for name, stats := range containers {
		if stats.State != "running" {
			recs = append(recs, fmt.Sprintf("⚠️  %s is not running (state: %s)", name, stats.State))
			continue
		}

		// Memory warnings
		if stats.MemoryPercent > 80 {
			recs = append(recs, fmt.Sprintf("🔴 %s memory usage is critical (%.0f%%). Consider increasing memory limit.", name, stats.MemoryPercent))
		} else if stats.MemoryPercent > 60 {
			recs = append(recs, fmt.Sprintf("🟡 %s memory usage is elevated (%.0f%%). Monitor closely.", name, stats.MemoryPercent))
		}

		// CPU warnings
		if stats.CPUPercent > 80 {
			recs = append(recs, fmt.Sprintf("🔴 %s CPU usage is high (%.1f%%). Consider scaling.", name, stats.CPUPercent))
		}
	}

	if len(recs) == 0 {
		recs = append(recs, "✅ All services are healthy")
	}

	return recs
}

func formatDuration(d time.Duration) string {
	days := int(d.Hours() / 24)
	hours := int(d.Hours()) % 24
	minutes := int(d.Minutes()) % 60

	if days > 0 {
		return fmt.Sprintf("%dd %dh %dm", days, hours, minutes)
	}
	if hours > 0 {
		return fmt.Sprintf("%dh %dm", hours, minutes)
	}
	return fmt.Sprintf("%dm", minutes)
}
