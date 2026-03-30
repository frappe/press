package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"syscall"
	"time"
)

func performRecovery(cfg Config, triggers []string, dbHealth DBHealth, creds MySQLCredentials, frozen *frozenState) bool {
	slog.Error("recovery triggered",
		"triggers", triggers,
		"mariadb_reachable", dbHealth.Reachable,
		"stuck_queries", dbHealth.StuckQueries,
		"details", dbHealth.Details,
	)

	isFrozen := false
	reason := ""
	if frozen != nil {
		isFrozen = frozen.frozen
		reason = frozen.reason
	} else {
		isFrozen, reason = checkMachineFrozen()
	}

	if !isFrozen && shouldTakeCoredump(cfg, dbHealth, len(triggers)) {
		if err := takeCoredump(cfg); err != nil {
			slog.Warn("coredump failed, continuing with recovery", "error", err)
		}
	}

	if isFrozen {
		slog.Warn("machine appears frozen, skipping graceful stop and killing mariadb directly", "reason", reason)
		killMariaDB()
	} else if !stopMariaDB(cfg.StopTimeout) {
		killMariaDB()
	}

	reclaimMemory(cfg.DropCachesMode)
	startMariaDB(creds)

	return true
}

func stopMariaDB(timeout time.Duration) bool {
	slog.Info("stopping mariadb via systemctl", "timeout", timeout)

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "systemctl", "stop", "mariadb")
	output, err := cmd.CombinedOutput()

	if ctx.Err() == context.DeadlineExceeded {
		slog.Warn("systemctl stop mariadb timed out", "timeout", timeout)
		return false
	}

	if err != nil {
		slog.Warn("systemctl stop mariadb failed", "error", err, "output", string(output))
		return false
	}

	slog.Info("mariadb stopped gracefully")
	return true
}

func killMariaDB() {
	slog.Warn("sending SIGKILL to mariadbd")

	for _, pid := range findMariaDBProcessIDs() {
		proc, err := os.FindProcess(pid)
		if err != nil {
			continue
		}
		if err := proc.Signal(syscall.SIGKILL); err != nil {
			slog.Warn("failed to SIGKILL process", "pid", pid, "error", err)
		} else {
			slog.Info("sent SIGKILL to process", "pid", pid)
		}
	}

	time.Sleep(2 * time.Second)
}

func reclaimMemory(dropMode int) {
	slog.Info("reclaiming memory", "drop_caches_mode", dropMode)

	// Use syscall.Sync to avoid forking during memory pressure
	syscall.Sync()

	if err := os.WriteFile("/proc/sys/vm/drop_caches", []byte(fmt.Sprintf("%d", dropMode)), 0644); err != nil {
		slog.Warn("failed to drop caches", "error", err)
	} else {
		slog.Info("dropped caches", "mode", dropMode)
	}

	if err := os.WriteFile("/proc/sys/vm/compact_memory", []byte("1"), 0644); err != nil {
		slog.Debug("compact_memory not available", "error", err)
	} else {
		slog.Info("triggered memory compaction")
	}
}

func startMariaDB(creds MySQLCredentials) {
	slog.Info("starting mariadb via systemctl")

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "systemctl", "start", "mariadb")
	output, err := cmd.CombinedOutput()

	if err != nil {
		slog.Error("failed to start mariadb", "error", err, "output", string(output))
		return
	}

	slog.Info("mariadb started, verifying health")

	for i := 0; i < 5; i++ {
		time.Sleep(2 * time.Second)
		if checkReachable(creds) {
			slog.Info("mariadb is reachable after restart")
			return
		}
	}

	slog.Warn("mariadb started but is not reachable (socket/TCP) after 10s")
}
