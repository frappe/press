package main

import (
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"syscall"
	"time"
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

// findProcessIDsByName returns PIDs whose /proc/<pid>/comm matches any of
// the given names. Protected names are silently dropped. PID 1 is skipped.
func findProcessIDsByName(names []string) map[string][]int {
	wanted := map[string]bool{}
	for _, n := range names {
		n = strings.ToLower(strings.TrimSpace(n))
		if n == "" || isProtectedProcessName(n) {
			continue
		}
		wanted[n] = true
	}
	if len(wanted) == 0 {
		return nil
	}

	files, err := os.ReadDir("/proc")
	if err != nil {
		return nil
	}

	out := map[string][]int{}
	for _, f := range files {
		if !f.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(f.Name())
		if err != nil || pid == 1 {
			continue
		}
		data, err := os.ReadFile(fmt.Sprintf("/proc/%d/comm", pid))
		if err != nil {
			continue
		}
		comm := strings.ToLower(strings.TrimSpace(string(data)))
		if wanted[comm] {
			out[comm] = append(out[comm], pid)
		}
	}
	return out
}

// killProcessesByName SIGKILLs every process whose comm matches one of names.
// Returns the number of processes that received the signal.
func killProcessesByName(names []string) int {
	matches := findProcessIDsByName(names)
	if len(matches) == 0 {
		return 0
	}
	killed := 0
	for name, pids := range matches {
		for _, pid := range pids {
			proc, err := os.FindProcess(pid)
			if err != nil {
				continue
			}
			if err := proc.Signal(syscall.SIGKILL); err != nil {
				slog.Warn("failed to SIGKILL killable process",
					"name", name, "pid", pid, "error", err)
				continue
			}
			slog.Warn("SIGKILLed process to relieve memory pressure",
				"name", name, "pid", pid)
			killed++
		}
	}
	if killed > 0 {
		time.Sleep(500 * time.Millisecond)
	}
	return killed
}
