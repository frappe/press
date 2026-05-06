package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

// findMariaDBProcessIDs returns the PIDs of all running mariadbd/mysqld processes.
func findMariaDBProcessIDs() []int {
	files, err := os.ReadDir("/proc")
	if err != nil {
		return nil
	}

	var pids []int
	for _, f := range files {
		if !f.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(f.Name())
		if err != nil {
			continue
		}
		data, err := os.ReadFile(fmt.Sprintf("/proc/%d/comm", pid))
		if err != nil {
			continue
		}
		comm := strings.TrimSpace(string(data))
		if comm == "mariadbd" || comm == "mysqld" {
			pids = append(pids, pid)
		}
	}
	return pids
}
