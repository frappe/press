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

	killed := false
	if isFrozen {
		slog.Warn("machine appears frozen, skipping graceful stop and killing mariadb directly", "reason", reason)
		killed = killMariaDB()
	} else if !stopMariaDB(cfg.StopTimeout) {
		killed = killMariaDB()
	} else {
		killed = true // graceful stop succeeded
	}

	if !killed {
		slog.Error("failed to stop/kill mariadb, rebooting machine")
		rebootMachine()
		return true
	}

	reclaimMemory(cfg.DropCachesMode)

	if !startMariaDB(creds) {
		slog.Error("failed to start mariadb after recovery, rebooting machine")
		rebootMachine()
		return true
	}

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

func killMariaDB() bool {
	slog.Warn("sending SIGKILL to mariadbd")

	// Use a channel+goroutine so PID lookup doesn't block forever on a frozen machine.
	type pidResult struct {
		pids []int
	}
	ch := make(chan pidResult, 1)
	go func() {
		ch <- pidResult{pids: findMariaDBProcessIDs()}
	}()

	var pids []int
	select {
	case r := <-ch:
		pids = r.pids
	case <-time.After(5 * time.Second):
		slog.Error("findMariaDBProcessIDs timed out (I/O freeze?)")
		return false
	}

	if len(pids) == 0 {
		slog.Error("cannot find mariadbd/mysqld process to kill")
		return false
	}

	allFailed := true
	for _, pid := range pids {
		proc, err := os.FindProcess(pid)
		if err != nil {
			continue
		}
		if err := proc.Signal(syscall.SIGKILL); err != nil {
			slog.Warn("failed to SIGKILL process", "pid", pid, "error", err)
		} else {
			slog.Info("sent SIGKILL to process", "pid", pid)
			allFailed = false
		}
	}

	if allFailed {
		slog.Error("failed to SIGKILL any mariadb process")
		return false
	}

	time.Sleep(2 * time.Second)
	return true
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

func startMariaDB(creds MySQLCredentials) bool {
	slog.Info("starting mariadb via systemctl")

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "systemctl", "start", "mariadb")
	output, err := cmd.CombinedOutput()

	if err != nil {
		slog.Error("failed to start mariadb", "error", err, "output", string(output))
		return false
	}

	slog.Info("mariadb started, verifying health")

	for i := 0; i < 5; i++ {
		time.Sleep(2 * time.Second)
		if checkReachable(creds) {
			slog.Info("mariadb is reachable after restart")
			return true
		}
	}

	slog.Warn("mariadb started but is not reachable (socket/TCP) after 10s")
	return false
}

func rebootMachine() {
	slog.Error("initiating machine reboot via syscall")
	syscall.Reboot(syscall.LINUX_REBOOT_CMD_RESTART)
}
