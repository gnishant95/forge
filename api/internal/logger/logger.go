// Package logger provides structured JSON logging for Forge API
// Uses zerolog for high-performance structured logging
//
// Log format:
//
//	{"timestamp":"...","level":"info","service":"api","endpoint":"/api/v1/health","msg":"..."}
package logger

import (
	"os"
	"time"

	"github.com/rs/zerolog"
)

var log zerolog.Logger

func init() {
	// Configure zerolog for JSON output with consistent field names
	zerolog.TimeFieldFormat = time.RFC3339
	zerolog.TimestampFieldName = "timestamp"
	zerolog.LevelFieldName = "level"
	zerolog.MessageFieldName = "msg"

	log = zerolog.New(os.Stdout).With().
		Timestamp().
		Str("service", "api").
		Logger()
}

// Get returns the configured logger instance
func Get() zerolog.Logger {
	return log
}

// WithEndpoint returns a logger with endpoint context
func WithEndpoint(endpoint string) zerolog.Logger {
	return log.With().Str("endpoint", endpoint).Logger()
}

// WithMethod returns a logger with method and endpoint context
func WithMethod(method, endpoint string) zerolog.Logger {
	return log.With().
		Str("method", method).
		Str("endpoint", endpoint).
		Logger()
}

// Info logs an info message
func Info(msg string) {
	log.Info().Msg(msg)
}

// Error logs an error message with error details
func Error(msg string, err error) {
	log.Error().Err(err).Msg(msg)
}

// Warn logs a warning message
func Warn(msg string) {
	log.Warn().Msg(msg)
}

// Debug logs a debug message
func Debug(msg string) {
	log.Debug().Msg(msg)
}

// RequestLog logs an HTTP request with standard fields
func RequestLog(method, endpoint string, status int, duration time.Duration, err error) {
	event := log.Info()
	if status >= 500 {
		event = log.Error()
	} else if status >= 400 {
		event = log.Warn()
	}

	event.
		Str("method", method).
		Str("endpoint", endpoint).
		Int("status", status).
		Dur("duration_ms", duration).
		Err(err).
		Msg("request")
}

