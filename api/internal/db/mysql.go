package db

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

type MySQLClient struct {
	db *sql.DB
}

func NewMySQLClient() (*MySQLClient, error) {
	host := os.Getenv("MYSQL_HOST")
	if host == "" {
		host = "localhost"
	}
	port := os.Getenv("MYSQL_PORT")
	if port == "" {
		port = "3306"
	}
	user := os.Getenv("MYSQL_USER")
	if user == "" {
		user = "root"
	}
	password := os.Getenv("MYSQL_PASSWORD")
	if password == "" {
		password = "forgeroot"
	}
	
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/", user, password, host, port)
	
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return nil, err
	}
	
	// Retry connection with backoff (MySQL might still be starting)
	maxRetries := 10
	var lastErr error
	for i := 0; i < maxRetries; i++ {
		if err := db.Ping(); err == nil {
			return &MySQLClient{db: db}, nil
		} else {
			lastErr = err
	}
	
		// Wait before retrying (1s, 2s, 3s, ... up to 5s)
		waitTime := time.Duration(min(i+1, 5)) * time.Second
		time.Sleep(waitTime)
	}
	
	return nil, fmt.Errorf("failed to connect after %d retries: %w", maxRetries, lastErr)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func (c *MySQLClient) Ping(ctx context.Context) error {
	return c.db.PingContext(ctx)
}

func (c *MySQLClient) Query(ctx context.Context, query string, database string) ([]map[string]string, []string, error) {
	db := c.db
	
	// If database specified, use it
	if database != "" {
		_, err := db.ExecContext(ctx, "USE "+database)
		if err != nil {
			return nil, nil, err
		}
	}
	
	rows, err := db.QueryContext(ctx, query)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()
	
	columns, err := rows.Columns()
	if err != nil {
		return nil, nil, err
	}
	
	var results []map[string]string
	
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}
		
		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, nil, err
		}
		
		row := make(map[string]string)
		for i, col := range columns {
			val := values[i]
			if val == nil {
				row[col] = ""
			} else {
				switch v := val.(type) {
				case []byte:
					row[col] = string(v)
				default:
					row[col] = fmt.Sprintf("%v", v)
				}
			}
		}
		results = append(results, row)
	}
	
	return results, columns, nil
}

func (c *MySQLClient) Execute(ctx context.Context, query string, database string) (int64, int64, error) {
	db := c.db
	
	if database != "" {
		_, err := db.ExecContext(ctx, "USE "+database)
		if err != nil {
			return 0, 0, err
		}
	}
	
	result, err := db.ExecContext(ctx, query)
	if err != nil {
		return 0, 0, err
	}
	
	affected, _ := result.RowsAffected()
	lastID, _ := result.LastInsertId()
	
	return affected, lastID, nil
}

func (c *MySQLClient) Close() error {
	return c.db.Close()
}

