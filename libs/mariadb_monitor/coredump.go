package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

func shouldTakeCoredump(cfg Config, dbHealth DBHealth, triggerCount int) bool {
	if !cfg.CoredumpEnabled {
		return false
	}

	if cfg.CoredumpOnUnhealthy && (!dbHealth.Reachable || dbHealth.IsStuck) {
		slog.Info("coredump: DB is unhealthy, coredump warranted")
		return true
	}

	if cfg.CoredumpOnFrequentTriggers && triggerCount >= cfg.CoredumpFrequentThreshold {
		slog.Info("coredump: frequent triggers detected", "trigger_count", triggerCount, "threshold", cfg.CoredumpFrequentThreshold)
		return true
	}

	return false
}

func takeCoredump(cfg Config) error {
	pids := findMariaDBProcessIDs()
	if len(pids) == 0 {
		return fmt.Errorf("mariadbd/mysqld process not found")
	}
	pid := pids[0]

	if err := os.MkdirAll(cfg.CoredumpOutputDir, 0755); err != nil {
		return fmt.Errorf("create coredump dir: %w", err)
	}

	timestamp := time.Now().Format("20060102_150405")
	outputPrefix := filepath.Join(cfg.CoredumpOutputDir, fmt.Sprintf("mariadb_%s", timestamp))

	slog.Info("taking coredump via gcore", "pid", pid, "output", outputPrefix)

	ctx, cancel := context.WithTimeout(context.Background(), cfg.CoredumpTimeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "gcore", "-o", outputPrefix, strconv.Itoa(pid))
	output, err := cmd.CombinedOutput()

	if ctx.Err() == context.DeadlineExceeded {
		return fmt.Errorf("gcore timed out after %s", cfg.CoredumpTimeout)
	}

	if err != nil {
		return fmt.Errorf("gcore failed: %w, output: %s", err, string(output))
	}

	slog.Info("coredump captured successfully", "output", outputPrefix)

	cleanupOldCoredumps(cfg.CoredumpOutputDir, cfg.CoredumpMaxCount)
	return nil
}

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

func cleanupOldCoredumps(dir string, maxCount int) {
	if maxCount <= 0 {
		return
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		slog.Warn("coredump cleanup: failed to read dir", "dir", dir, "error", err)
		return
	}

	var coreFiles []os.DirEntry
	for _, e := range entries {
		if !e.IsDir() && strings.HasPrefix(e.Name(), "mariadb_") {
			coreFiles = append(coreFiles, e)
		}
	}

	if len(coreFiles) <= maxCount {
		return
	}

	sort.Slice(coreFiles, func(i, j int) bool {
		return coreFiles[i].Name() < coreFiles[j].Name()
	})

	toRemove := coreFiles[:len(coreFiles)-maxCount]
	for _, f := range toRemove {
		path := filepath.Join(dir, f.Name())
		if err := os.Remove(path); err != nil {
			slog.Warn("coredump cleanup: failed to remove", "path", path, "error", err)
		} else {
			slog.Info("coredump cleanup: removed old coredump", "path", path)
		}
	}
}
