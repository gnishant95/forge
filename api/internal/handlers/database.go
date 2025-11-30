package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"os"

	"connectrpc.com/connect"
	forgev1 "github.com/forge/api/gen/forge/v1"
	"github.com/forge/api/internal/db"
)

type DatabaseHandler struct {
	mysqlClient *db.MySQLClient
}

func NewDatabaseHandler(mysql *db.MySQLClient) *DatabaseHandler {
	return &DatabaseHandler{
		mysqlClient: mysql,
	}
}

func (h *DatabaseHandler) Query(
	ctx context.Context,
	req *connect.Request[forgev1.QueryRequest],
) (*connect.Response[forgev1.QueryResponse], error) {
	if h.mysqlClient == nil {
		return nil, connect.NewError(connect.CodeUnavailable, nil)
	}
	
	rows, columns, err := h.mysqlClient.Query(ctx, req.Msg.Sql, req.Msg.Database)
	if err != nil {
		return nil, connect.NewError(connect.CodeInternal, err)
	}
	
	protoRows := make([]*forgev1.Row, len(rows))
	for i, row := range rows {
		protoRows[i] = &forgev1.Row{Values: row}
	}
	
	return connect.NewResponse(&forgev1.QueryResponse{
		Rows:     protoRows,
		Columns:  columns,
		RowCount: int64(len(rows)),
	}), nil
}

func (h *DatabaseHandler) Execute(
	ctx context.Context,
	req *connect.Request[forgev1.ExecuteRequest],
) (*connect.Response[forgev1.ExecuteResponse], error) {
	if h.mysqlClient == nil {
		return nil, connect.NewError(connect.CodeUnavailable, nil)
	}
	
	affected, lastID, err := h.mysqlClient.Execute(ctx, req.Msg.Sql, req.Msg.Database)
	if err != nil {
		return nil, connect.NewError(connect.CodeInternal, err)
	}
	
	return connect.NewResponse(&forgev1.ExecuteResponse{
		RowsAffected: affected,
		LastInsertId: lastID,
	}), nil
}

func (h *DatabaseHandler) GetInfo(
	ctx context.Context,
	req *connect.Request[forgev1.GetInfoRequest],
) (*connect.Response[forgev1.GetInfoResponse], error) {
	port := getEnvOrDefault("MYSQL_PORT", "3306")
	user := getEnvOrDefault("MYSQL_USER", "root")
	password := getEnvOrDefault("MYSQL_PASSWORD", "forgeroot")
	
	// External host (for SDK clients outside Docker)
	host := getEnvOrDefault("EXTERNAL_HOST", "localhost")
	
	return connect.NewResponse(&forgev1.GetInfoResponse{
		Host:     host,
		Port:     3306,
		User:     user,
		Password: password,
		Url:      "mysql+pymysql://" + user + ":" + password + "@" + host + ":" + port,
	}), nil
}

func getEnvOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

// REST handlers
func QueryREST(h *DatabaseHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		
		var req forgev1.QueryRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		
		resp, err := h.Query(r.Context(), connect.NewRequest(&req))
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp.Msg)
	}
}

func DBInfoREST(h *DatabaseHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		resp, err := h.GetInfo(r.Context(), connect.NewRequest(&forgev1.GetInfoRequest{}))
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp.Msg)
	}
}

