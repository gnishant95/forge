package cache

import (
	"context"
	"os"
	"time"

	"github.com/redis/go-redis/v9"
)

type RedisClient struct {
	client *redis.Client
}

func NewRedisClient() (*RedisClient, error) {
	host := os.Getenv("REDIS_HOST")
	if host == "" {
		host = "localhost"
	}
	port := os.Getenv("REDIS_PORT")
	if port == "" {
		port = "6379"
	}
	password := os.Getenv("REDIS_PASSWORD")

	client := redis.NewClient(&redis.Options{
		Addr:     host + ":" + port,
		Password: password,
		DB:       0,
	})

	// Retry connection with backoff (Redis might still be starting)
	maxRetries := 10
	var lastErr error
	for i := 0; i < maxRetries; i++ {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		err := client.Ping(ctx).Err()
		cancel()
		if err == nil {
			return &RedisClient{client: client}, nil
		} else {
			lastErr = err
		}

		// Wait before retrying (1s, 2s, 3s, ... up to 5s), but not after the last attempt
		if i < maxRetries-1 {
			waitTime := time.Duration(min(i+1, 5)) * time.Second
			time.Sleep(waitTime)
		}
	}

	client.Close() // Clean up the client since we failed to connect
	return nil, lastErr
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func (c *RedisClient) Ping(ctx context.Context) error {
	return c.client.Ping(ctx).Err()
}

func (c *RedisClient) Get(ctx context.Context, key string) (string, bool, error) {
	val, err := c.client.Get(ctx, key).Result()
	if err == redis.Nil {
		return "", false, nil
	}
	if err != nil {
		return "", false, err
	}
	return val, true, nil
}

func (c *RedisClient) Set(ctx context.Context, key, value string, ttl time.Duration) error {
	return c.client.Set(ctx, key, value, ttl).Err()
}

func (c *RedisClient) Delete(ctx context.Context, key string) (bool, error) {
	result, err := c.client.Del(ctx, key).Result()
	if err != nil {
		return false, err
	}
	return result > 0, nil
}

func (c *RedisClient) Close() error {
	return c.client.Close()
}
