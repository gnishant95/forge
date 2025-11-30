package main

import (
	"log"
	"net/http"
	"os"
	"time"

	"github.com/forge/api/gen/forge/v1/forgev1connect"
	"github.com/forge/api/internal/cache"
	"github.com/forge/api/internal/db"
	"github.com/forge/api/internal/handlers"
	"github.com/forge/api/internal/observe"
	"github.com/rs/cors"
	"golang.org/x/net/http2"
	"golang.org/x/net/http2/h2c"
)

var startTime = time.Now()

func main() {
	// Configuration from environment
	port := getEnv("PORT", "8080")
	
	// Initialize clients
	mysqlClient, err := db.NewMySQLClient()
	if err != nil {
		log.Printf("Warning: MySQL not available: %v", err)
	}
	
	redisClient, err := cache.NewRedisClient()
	if err != nil {
		log.Printf("Warning: Redis not available: %v", err)
	}
	
	lokiClient := observe.NewLokiClient()
	
	// Create handlers
	forgeHandler := handlers.NewForgeHandler(startTime, mysqlClient, redisClient)
	dbHandler := handlers.NewDatabaseHandler(mysqlClient)
	cacheHandler := handlers.NewCacheHandler(redisClient)
	observeHandler := handlers.NewObserveHandler(lokiClient)
	
	// Create mux
	mux := http.NewServeMux()
	
	// Register Connect services
	mux.Handle(forgev1connect.NewForgeServiceHandler(forgeHandler))
	mux.Handle(forgev1connect.NewDatabaseServiceHandler(dbHandler))
	mux.Handle(forgev1connect.NewCacheServiceHandler(cacheHandler))
	mux.Handle(forgev1connect.NewObserveServiceHandler(observeHandler))
	
	// REST endpoints (for compatibility)
	mux.HandleFunc("/api/v1/health", handlers.HealthREST(forgeHandler))
	mux.HandleFunc("/api/v1/info", handlers.InfoREST(forgeHandler))
	mux.HandleFunc("/api/v1/db/query", handlers.QueryREST(dbHandler))
	mux.HandleFunc("/api/v1/db/info", handlers.DBInfoREST(dbHandler))
	mux.HandleFunc("/api/v1/cache/", handlers.CacheREST(cacheHandler))
	mux.HandleFunc("/api/v1/cache/info", handlers.CacheInfoREST(cacheHandler))
	mux.HandleFunc("/api/v1/logs", handlers.LogsREST(observeHandler))
	mux.HandleFunc("/api/v1/metrics", handlers.MetricsREST(observeHandler))
	mux.HandleFunc("/api/v1/traces", handlers.TracesREST(observeHandler))
	
	// Swagger docs
	mux.HandleFunc("/docs", handlers.SwaggerUI)
	mux.HandleFunc("/docs/", handlers.SwaggerUI)
	mux.HandleFunc("/openapi.json", handlers.OpenAPISpec)
	
	// CORS middleware
	corsHandler := cors.New(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"*"},
		AllowCredentials: true,
	}).Handler(mux)
	
	// HTTP/2 support for Connect
	handler := h2c.NewHandler(corsHandler, &http2.Server{})
	
	log.Printf("Forge API starting on :%s", port)
	log.Printf("REST:    http://localhost:%s/api/v1/", port)
	log.Printf("Connect: http://localhost:%s/forge.v1./", port)
	log.Printf("Docs:    http://localhost:%s/docs", port)
	
	if err := http.ListenAndServe(":"+port, handler); err != nil {
		log.Fatal(err)
	}
}

func getEnv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}

