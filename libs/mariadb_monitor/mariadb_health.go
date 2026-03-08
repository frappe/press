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

func checkProcesslist(creds MySQLCredentials, stuckThreshold time.Duration) DBHealth {
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

	var timeIdx, stateIdx, commandIdx, infoIdx int = -1, -1, -1, -1
	for i, col := range columns {
		switch col {
		case "Time":
			timeIdx = i
		case "State":
			stateIdx = i
		case "Command":
			commandIdx = i
		case "Info":
			infoIdx = i
		}
	}

	thresholdSecs := int64(stuckThreshold.Seconds())

	for rows.Next() {
		values := make([]sql.NullString, len(columns))
		ptrs := make([]interface{}, len(columns))
		for i := range values {
			ptrs[i] = &values[i]
		}

		if err := rows.Scan(ptrs...); err != nil {
			continue
		}

		if commandIdx >= 0 && values[commandIdx].Valid {
			cmd := values[commandIdx].String
			if cmd == "Sleep" || cmd == "Daemon" || cmd == "Binlog Dump" {
				continue
			}
		}

		isStuck := false
		reason := ""

		if stateIdx >= 0 && values[stateIdx].Valid {
			state := values[stateIdx].String
			switch state {
			case "Opening tables", "Killed":
				isStuck = true
				reason = fmt.Sprintf("state=%q", state)
			}
		}

		if timeIdx >= 0 && values[timeIdx].Valid && !isStuck {
			if queryTime, err := strconv.ParseInt(values[timeIdx].String, 10, 64); err == nil {
				if queryTime > thresholdSecs {
					isStuck = true
					reason = fmt.Sprintf("running for %ds (threshold %ds)", queryTime, thresholdSecs)
				}
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
