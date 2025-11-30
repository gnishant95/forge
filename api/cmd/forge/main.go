package main

import (
	"net/http"
	"os"
	"time"

	"github.com/forge/api/gen/forge/v1/forgev1connect"
	"github.com/forge/api/internal/cache"
	"github.com/forge/api/internal/db"
	"github.com/forge/api/internal/handlers"
	"github.com/forge/api/internal/logger"
	"github.com/forge/api/internal/logsources"
	"github.com/forge/api/internal/middleware"
	"github.com/forge/api/internal/observe"
	"github.com/forge/api/internal/routes"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/cors"
	"golang.org/x/net/http2"
	"golang.org/x/net/http2/h2c"
)

var startTime = time.Now()

func main() {
	log := logger.Get()

	// Configuration from environment
	port := getEnv("PORT", "8080")

	// Initialize clients
	mysqlClient, err := db.NewMySQLClient()
	if err != nil {
		log.Warn().Err(err).Msg("MySQL not available")
	}

	redisClient, err := cache.NewRedisClient()
	if err != nil {
		log.Warn().Err(err).Msg("Redis not available")
	}

	lokiClient := observe.NewLokiClient()

	// Initialize routes manager
	routesConfigPath := getEnv("ROUTES_CONFIG", "/app/data/routes/routes.yaml")
	nginxDynamicConf := getEnv("NGINX_DYNAMIC_CONF", "/app/data/routes/routes.conf")
	routesManager, err := routes.NewManager(routesConfigPath, nginxDynamicConf)
	if err != nil {
		log.Warn().Err(err).Msg("Routes manager init failed")
	}

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

	// Prometheus metrics endpoint
	mux.Handle("/metrics", promhttp.Handler())

	// REST endpoints
	mux.HandleFunc("/api/v1/health", handlers.HealthREST(forgeHandler))
	mux.HandleFunc("/api/v1/db/query", handlers.QueryREST(dbHandler))
	mux.HandleFunc("/api/v1/db/info", handlers.DBInfoREST(dbHandler))
	mux.HandleFunc("/api/v1/cache/", handlers.CacheREST(cacheHandler))
	mux.HandleFunc("/api/v1/cache/info", handlers.CacheInfoREST(cacheHandler))
	mux.HandleFunc("/api/v1/logs", handlers.LogsREST(observeHandler))
	mux.HandleFunc("/api/v1/metrics", handlers.MetricsREST(observeHandler))
	mux.HandleFunc("/api/v1/traces", handlers.TracesREST(observeHandler))

	// Routes management (dynamic nginx routes)
	if routesManager != nil {
		routesHandler := handlers.NewRoutesHandler(routesManager)
		mux.HandleFunc("/api/v1/routes", routesHandler.HandleRoutes)
		mux.HandleFunc("/api/v1/routes/", routesHandler.HandleRoutes)
	}

	// Log sources management (dynamic Promtail config)
	logSourcesConfigPath := getEnv("PROMTAIL_SOURCES_CONFIG", "/app/data/promtail/logsources.yaml")
	promtailDynamicConf := getEnv("PROMTAIL_DYNAMIC_CONF", "/app/data/promtail/promtail-dynamic.yml")
	logSourcesManager, err := logsources.NewManager(logSourcesConfigPath, promtailDynamicConf)
	if err != nil {
		log.Warn().Err(err).Msg("Log sources manager init failed")
	}
	if logSourcesManager != nil {
		logSourcesHandler := handlers.NewLogSourcesHandler(logSourcesManager)
		mux.HandleFunc("/api/v1/logs/sources", logSourcesHandler.HandleLogSources)
		mux.HandleFunc("/api/v1/logs/sources/", logSourcesHandler.HandleLogSources)
	}

	// System information (container stats, resources)
	systemHandler := handlers.NewSystemHandler()
	mux.HandleFunc("/api/v1/system", systemHandler.GetSystemInfo)

	// Swagger docs
	mux.HandleFunc("/docs", handlers.SwaggerUI)
	mux.HandleFunc("/docs/", handlers.SwaggerUI)
	mux.HandleFunc("/openapi.json", handlers.OpenAPISpec)

	// Apply metrics middleware
	metricsHandler := middleware.Metrics(mux)

	// CORS middleware
	corsHandler := cors.New(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"*"},
		AllowCredentials: true,
	}).Handler(metricsHandler)

	// HTTP/2 support for Connect
	handler := h2c.NewHandler(corsHandler, &http2.Server{})

	log.Info().
		Str("port", port).
		Str("rest", "http://localhost:"+port+"/api/v1/").
		Str("metrics", "http://localhost:"+port+"/metrics").
		Str("docs", "http://localhost:"+port+"/docs").
		Msg("Forge API starting")

	if err := http.ListenAndServe(":"+port, handler); err != nil {
		log.Fatal().Err(err).Msg("Server failed to start")
	}
}

func getEnv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}
