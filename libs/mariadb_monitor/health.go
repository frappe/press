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
)

type externalHealthResponse struct {
	Message struct {
		AppServerHealthy bool `json:"app_server_healthy"`
		DBServerHealthy  bool `json:"db_server_healthy"`
	} `json:"message"`
}

const externalHealthCheckTimeout = 90 * time.Second

func checkExternalDBHealth(cfg Config) (dbUnhealthy bool, ok bool) {
	if !cfg.External.Enabled {
		return false, false
	}
	if cfg.External.URL == "" || cfg.External.ServerName == "" || cfg.External.Token == "" {
		return false, false
	}

	body, err := json.Marshal(map[string]string{
		"name":  cfg.External.ServerName,
		"token": cfg.External.Token,
	})
	if err != nil {
		return false, false
	}

	req, err := http.NewRequest(http.MethodPost, cfg.External.URL, bytes.NewReader(body))
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

	if creds.Host != "" && creds.Port > 0 {
		checked = true
		tcpAddr := net.JoinHostPort(creds.Host, strconv.Itoa(creds.Port))
		conn, err := net.DialTimeout("tcp", tcpAddr, 3*time.Second)
		if err == nil {
			conn.Close()
			reachable = true
		}
	}

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

func checkMariaDBHealth(cfg Config, creds MySQLCredentials) DBHealth {
	if !checkReachable(creds) {
		slog.Warn("mariadb is unreachable", "socket", creds.Socket, "host", creds.Host, "port", creds.Port)
		return DBHealth{Reachable: false}
	}

	health := checkProcesslist(creds)
	if health.IsStuck {
		slog.Warn("mariadb has stuck queries", "stuck_count", health.StuckQueries, "details", health.Details)
		return health
	}

	slog.Debug("mariadb processlist is healthy")

	if dbUnhealthy, ok := checkExternalDBHealth(cfg); ok && dbUnhealthy {
		slog.Warn("external healthcheck reports db unhealthy, overriding local healthy verdict")
		health.IsStuck = true
		health.Details = append(health.Details, "external healthcheck: db_server_healthy=false")
	}
	return health
}

func checkProcesslist(creds MySQLCredentials) DBHealth {
	health := DBHealth{Reachable: true}
	db := NewDatabase(creds)

	var uptime int
	err := db.Query("SHOW GLOBAL STATUS LIKE 'Uptime'", func(rows *sql.Rows) error {
		if rows.Next() {
			var name, value string
			if err := rows.Scan(&name, &value); err != nil {
				return err
			}
			if v, err := strconv.Atoi(value); err == nil {
				uptime = v
			}
		}
		return nil
	})
	if err != nil {
		slog.Warn("failed to query mariadb uptime, defaulting to 3600", "error", err)
		uptime = 3600
	}

	err = db.Query("SHOW PROCESSLIST", func(rows *sql.Rows) error {
		columns, err := rows.Columns()
		if err != nil {
			return err
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
				if uptime > 600 && timeSec >= 300 {
					isStuck = true
					reason = fmt.Sprintf("state=%q time=%ds", state, timeSec)
				}
			case "Killed":
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
		return nil
	})
	if err != nil {
		health.Reachable = false
		return health
	}

	health.IsStuck = health.StuckQueries > 0
	return health
}
