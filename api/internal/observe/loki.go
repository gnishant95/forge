package observe

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"
)

type LokiClient struct {
	url    string
	client *http.Client
}

func NewLokiClient() *LokiClient {
	url := os.Getenv("LOKI_URL")
	if url == "" {
		url = "http://localhost:3100"
	}
	
	return &LokiClient{
		url:    url,
		client: &http.Client{Timeout: 10 * time.Second},
	}
}

// LokiPushRequest represents the Loki push API format
type LokiPushRequest struct {
	Streams []LokiStream `json:"streams"`
}

type LokiStream struct {
	Stream map[string]string `json:"stream"`
	Values [][]string        `json:"values"`
}

func (c *LokiClient) Push(ctx context.Context, level, message string, labels map[string]string) error {
	if level == "" {
		level = "info"
	}
	
	// Build stream labels
	streamLabels := map[string]string{
		"job":   "forge",
		"level": level,
	}
	for k, v := range labels {
		streamLabels[k] = v
	}
	
	// Current timestamp in nanoseconds
	ts := strconv.FormatInt(time.Now().UnixNano(), 10)
	
	// Create push request
	req := LokiPushRequest{
		Streams: []LokiStream{
			{
				Stream: streamLabels,
				Values: [][]string{
					{ts, message},
				},
			},
		},
	}
	
	body, err := json.Marshal(req)
	if err != nil {
		return err
	}
	
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.url+"/loki/api/v1/push", bytes.NewReader(body))
	if err != nil {
		return err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	
	resp, err := c.client.Do(httpReq)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode >= 400 {
		return fmt.Errorf("loki push failed: %d", resp.StatusCode)
	}
	
	return nil
}

