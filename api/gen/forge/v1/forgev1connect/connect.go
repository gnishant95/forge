// Package forgev1connect provides Connect service handlers
package forgev1connect

import (
	"context"
	"net/http"

	"connectrpc.com/connect"
	forgev1 "github.com/forge/api/gen/forge/v1"
)

// ForgeServiceHandler is the interface for ForgeService
type ForgeServiceHandler interface {
	Health(context.Context, *connect.Request[forgev1.HealthRequest]) (*connect.Response[forgev1.HealthResponse], error)
	Info(context.Context, *connect.Request[forgev1.InfoRequest]) (*connect.Response[forgev1.InfoResponse], error)
}

// DatabaseServiceHandler is the interface for DatabaseService
type DatabaseServiceHandler interface {
	Query(context.Context, *connect.Request[forgev1.QueryRequest]) (*connect.Response[forgev1.QueryResponse], error)
	Execute(context.Context, *connect.Request[forgev1.ExecuteRequest]) (*connect.Response[forgev1.ExecuteResponse], error)
	GetInfo(context.Context, *connect.Request[forgev1.GetInfoRequest]) (*connect.Response[forgev1.GetInfoResponse], error)
}

// CacheServiceHandler is the interface for CacheService
type CacheServiceHandler interface {
	Get(context.Context, *connect.Request[forgev1.GetRequest]) (*connect.Response[forgev1.GetResponse], error)
	Set(context.Context, *connect.Request[forgev1.SetRequest]) (*connect.Response[forgev1.SetResponse], error)
	Delete(context.Context, *connect.Request[forgev1.DeleteRequest]) (*connect.Response[forgev1.DeleteResponse], error)
	GetInfo(context.Context, *connect.Request[forgev1.CacheInfoRequest]) (*connect.Response[forgev1.CacheInfoResponse], error)
}

// ObserveServiceHandler is the interface for ObserveService
type ObserveServiceHandler interface {
	Log(context.Context, *connect.Request[forgev1.LogRequest]) (*connect.Response[forgev1.LogResponse], error)
	Metric(context.Context, *connect.Request[forgev1.MetricRequest]) (*connect.Response[forgev1.MetricResponse], error)
	Trace(context.Context, *connect.Request[forgev1.TraceRequest]) (*connect.Response[forgev1.TraceResponse], error)
}

// NewForgeServiceHandler creates HTTP handlers for ForgeService
func NewForgeServiceHandler(svc ForgeServiceHandler, opts ...connect.HandlerOption) (string, http.Handler) {
	mux := http.NewServeMux()
	
	mux.Handle("/forge.v1.ForgeService/Health", connect.NewUnaryHandler(
		"/forge.v1.ForgeService/Health",
		svc.Health,
		opts...,
	))
	mux.Handle("/forge.v1.ForgeService/Info", connect.NewUnaryHandler(
		"/forge.v1.ForgeService/Info",
		svc.Info,
		opts...,
	))
	
	return "/forge.v1.ForgeService/", mux
}

// NewDatabaseServiceHandler creates HTTP handlers for DatabaseService
func NewDatabaseServiceHandler(svc DatabaseServiceHandler, opts ...connect.HandlerOption) (string, http.Handler) {
	mux := http.NewServeMux()
	
	mux.Handle("/forge.v1.DatabaseService/Query", connect.NewUnaryHandler(
		"/forge.v1.DatabaseService/Query",
		svc.Query,
		opts...,
	))
	mux.Handle("/forge.v1.DatabaseService/Execute", connect.NewUnaryHandler(
		"/forge.v1.DatabaseService/Execute",
		svc.Execute,
		opts...,
	))
	mux.Handle("/forge.v1.DatabaseService/GetInfo", connect.NewUnaryHandler(
		"/forge.v1.DatabaseService/GetInfo",
		svc.GetInfo,
		opts...,
	))
	
	return "/forge.v1.DatabaseService/", mux
}

// NewCacheServiceHandler creates HTTP handlers for CacheService
func NewCacheServiceHandler(svc CacheServiceHandler, opts ...connect.HandlerOption) (string, http.Handler) {
	mux := http.NewServeMux()
	
	mux.Handle("/forge.v1.CacheService/Get", connect.NewUnaryHandler(
		"/forge.v1.CacheService/Get",
		svc.Get,
		opts...,
	))
	mux.Handle("/forge.v1.CacheService/Set", connect.NewUnaryHandler(
		"/forge.v1.CacheService/Set",
		svc.Set,
		opts...,
	))
	mux.Handle("/forge.v1.CacheService/Delete", connect.NewUnaryHandler(
		"/forge.v1.CacheService/Delete",
		svc.Delete,
		opts...,
	))
	mux.Handle("/forge.v1.CacheService/GetInfo", connect.NewUnaryHandler(
		"/forge.v1.CacheService/GetInfo",
		svc.GetInfo,
		opts...,
	))
	
	return "/forge.v1.CacheService/", mux
}

// NewObserveServiceHandler creates HTTP handlers for ObserveService
func NewObserveServiceHandler(svc ObserveServiceHandler, opts ...connect.HandlerOption) (string, http.Handler) {
	mux := http.NewServeMux()
	
	mux.Handle("/forge.v1.ObserveService/Log", connect.NewUnaryHandler(
		"/forge.v1.ObserveService/Log",
		svc.Log,
		opts...,
	))
	mux.Handle("/forge.v1.ObserveService/Metric", connect.NewUnaryHandler(
		"/forge.v1.ObserveService/Metric",
		svc.Metric,
		opts...,
	))
	mux.Handle("/forge.v1.ObserveService/Trace", connect.NewUnaryHandler(
		"/forge.v1.ObserveService/Trace",
		svc.Trace,
		opts...,
	))
	
	return "/forge.v1.ObserveService/", mux
}

