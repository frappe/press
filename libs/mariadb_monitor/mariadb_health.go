package main

import (
	"database/sql"
	"fmt"
	"log/slog"
	"net"
	"strconv"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

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
