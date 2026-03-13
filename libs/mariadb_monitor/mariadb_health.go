package main

import (
	"database/sql"
	"fmt"
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

func checkReachable(socketPath string) bool {
	conn, err := net.DialTimeout("unix", socketPath, 3*time.Second)
	if err != nil {
		return false
	}
	conn.Close()
	return true
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
	err = db.QueryRow("SHOW GLOBAL STATUS LIKE 'Uptime'").Scan(&varName, &varValue)
	if parsedUptime, convErr := strconv.Atoi(varValue); convErr == nil {
		uptime = parsedUptime
	} else {
		uptime = 3600 // Default to a safe high value if it fails
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
