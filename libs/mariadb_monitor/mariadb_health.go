package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"strconv"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

// externalHealthResponse mirrors the JSON returned by the press API endpoint.
type externalHealthResponse struct {
	Message struct {
		AppServerHealthy bool `json:"app_server_healthy"`
		DBServerHealthy  bool `json:"db_server_healthy"`
	} `json:"message"`
}

const externalHealthCheckTimeout = 90 * time.Second

// checkExternalDBHealth queries an external API for a second opinion on db
// health. It returns (dbUnhealthy, ok). ok is false when the result should be
// ignored (disabled, missing config, transport error/timeout, non-200 response,
// malformed body, or app server reported unhealthy). The default http.Client
// follows 301/302/303/307/308 redirects automatically.
func checkExternalDBHealth(cfg Config) (dbUnhealthy bool, ok bool) {
	if !cfg.ExternalHealthCheckEnabled {
		return false, false
	}
	if cfg.ExternalHealthCheckURL == "" || cfg.ServerName == "" || cfg.ExternalHealthCheckToken == "" {
		return false, false
	}

	body, err := json.Marshal(map[string]string{
		"name":  cfg.ServerName,
		"token": cfg.ExternalHealthCheckToken,
	})
	if err != nil {
		return false, false
	}

	req, err := http.NewRequest(http.MethodPost, cfg.ExternalHealthCheckURL, bytes.NewReader(body))
	if err != nil {
		slog.Warn("external healthcheck: building request failed", "error", err)
		return false, false
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	client := &http.Client{Timeout: externalHealthCheckTimeout}

	resp, err := client.Do(req)
	if err != nil {
		slog.Warn("external healthcheck: request failed", "error", err)
		return false, false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		slog.Warn("external healthcheck: non-200 response, ignoring", "status", resp.StatusCode)
		return false, false
	}

	var out externalHealthResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		slog.Warn("external healthcheck: decode failed", "error", err)
		return false, false
	}

	if !out.Message.AppServerHealthy {
		slog.Info("external healthcheck: app server unhealthy, ignoring db verdict")
		return false, false
	}

	return !out.Message.DBServerHealthy, true
}

type DBHealth struct {
	Reachable    bool
	StuckQueries int
	IsStuck      bool
	Details      []string
}

func checkReachable(creds MySQLCredentials) bool {
	checked := false
	reachable := false

	// Prefer TCP if host and port are configured.
	if creds.Host != "" && creds.Port > 0 {
		checked = true
		tcpAddr := net.JoinHostPort(creds.Host, strconv.Itoa(creds.Port))
		conn, err := net.DialTimeout("tcp", tcpAddr, 3*time.Second)
		if err == nil {
			conn.Close()
			reachable = true
		}
	}

	// Fall back to Unix socket only if TCP is not configured or failed.
	if !reachable && creds.Socket != "" {
		checked = true
		conn, err := net.DialTimeout("unix", creds.Socket, 3*time.Second)
		if err == nil {
			conn.Close()
			reachable = true
		}
	}

	if !checked {
		slog.Warn("no connection method configured, skipping reachability check")
		return true
	}

	return reachable
}

func checkProcesslist(creds MySQLCredentials) DBHealth {
	health := DBHealth{Reachable: true}

	dsn := fmt.Sprintf("%s:%s@unix(%s)/?timeout=5s&readTimeout=5s&writeTimeout=5s", creds.User, creds.Password, creds.Socket)
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		health.Reachable = false
		return health
	}
	defer db.Close()

	db.SetConnMaxLifetime(5 * time.Second)
	db.SetMaxOpenConns(1)

	var uptime int
	var varName, varValue string
	if err = db.QueryRow("SHOW GLOBAL STATUS LIKE 'Uptime'").Scan(&varName, &varValue); err != nil {
		slog.Warn("failed to query mariadb uptime, defaulting to 3600", "error", err)
		uptime = 3600
	} else if parsedUptime, convErr := strconv.Atoi(varValue); convErr == nil {
		uptime = parsedUptime
	} else {
		slog.Warn("failed to parse mariadb uptime value, defaulting to 3600", "value", varValue)
		uptime = 3600
	}

	rows, err := db.Query("SHOW PROCESSLIST")
	if err != nil {
		health.Reachable = false
		return health
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		health.Reachable = false
		return health
	}

	var stateIdx, infoIdx, timeIdx int = -1, -1, -1
	for i, col := range columns {
		switch col {
		case "State":
			stateIdx = i
		case "Info":
			infoIdx = i
		case "Time":
			timeIdx = i
		}
	}

	for rows.Next() {
		values := make([]sql.NullString, len(columns))
		ptrs := make([]interface{}, len(columns))
		for i := range values {
			ptrs[i] = &values[i]
		}

		if err := rows.Scan(ptrs...); err != nil {
			continue
		}

		// Only flag processes that are explicitly in a known-stuck state.
		// We only act on states where MariaDB itself is blocked/stuck.
		if stateIdx < 0 || !values[stateIdx].Valid {
			continue
		}

		state := values[stateIdx].String
		isStuck := false
		reason := ""

		var timeSec int
		if timeIdx >= 0 && values[timeIdx].Valid {
			timeSec, _ = strconv.Atoi(values[timeIdx].String)
		}

		switch state {
		case "Opening tables":
			// If MariaDB recently started (e.g., uptime < 10 mins), Opening tables is normal.
			// Otherwise, if it has been opening for > 5 minutes, consider it stuck.
			if uptime > 600 && timeSec >= 300 {
				isStuck = true
				reason = fmt.Sprintf("state=%q time=%ds", state, timeSec)
			}
		case "Killed":
			// If a killed process is stuck for > 5 mins
			if timeSec >= 300 {
				isStuck = true
				reason = fmt.Sprintf("state=%q time=%ds", state, timeSec)
			}
		}

		if isStuck {
			health.StuckQueries++
			info := ""
			if infoIdx >= 0 && values[infoIdx].Valid {
				info = values[infoIdx].String
				if len(info) > 100 {
					info = info[:100] + "..."
				}
			}
			health.Details = append(health.Details, fmt.Sprintf("%s query=%q", reason, info))
		}
	}

	health.IsStuck = health.StuckQueries > 0
	return health
}
