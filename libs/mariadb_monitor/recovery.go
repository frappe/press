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

const (
	// Always drop the page cache after a recovery. Modes 2 and 3 also drop
	// dentries/inodes which is rarely useful and can stall the system.
	dropCachesMode = 1

	// How long to wait for mariadbd processes to actually disappear after we
	// asked systemd to kill them. SIGKILL is immediate but the kernel still
	// needs to reap, flush dirty pages, release locks, etc.
	processDeathTimeout = 30 * time.Second

	// Poll interval while waiting for mariadbd to disappear.
	processDeathPoll = 200 * time.Millisecond

	// How long to wait for mariadb to become reachable after start.
	mariadbReachableTimeout = 3 * time.Minute
	mariadbReachablePoll    = 5 * time.Second
)

// resolveFrozenState returns the frozen flag and reason, querying the machine
// directly only when a pre-computed frozen state was not provided.
func resolveFrozenState(frozen *frozenState) (bool, string) {
	if frozen != nil {
		return frozen.frozen, frozen.reason
	}
	return checkMachineFrozen()
}

func performRecovery(cfg Config, triggers []string, dbHealth DBHealth, creds MySQLCredentials, frozen *frozenState) bool {
	slog.Error("recovery triggered",
		"triggers", triggers,
		"mariadb_reachable", dbHealth.Reachable,
		"stuck_queries", dbHealth.StuckQueries,
		"details", dbHealth.Details,
	)

	isFrozen, reason := resolveFrozenState(frozen)
	if isFrozen {
		slog.Warn("machine appears frozen, skipping coredump", "reason", reason)
	} else if shouldTakeCoredump(cfg) {
		if err := takeCoredump(cfg); err != nil {
			slog.Warn("coredump failed, continuing with recovery", "error", err)
		}
	}

	// Force-kill the unit through systemd. This is faster and more reliable
	// than trying a graceful TERM first: if mariadbd is healthy enough to
	// shut down gracefully, the monitor would not be in this code path.
	killMariaDB()

	if !waitForProcessDeath(processDeathTimeout) {
		slog.Error("mariadbd processes still alive after force kill, hard-rebooting")
		forceSystemReboot("mariadbd_kill_failed")
		return true
	}

	reclaimMemory()

	if !startMariaDB(creds) {
		slog.Error("mariadb did not come back after start, hard-rebooting")
		forceSystemReboot("mariadb_start_failed")
		return true
	}

	return true
}

// killMariaDB asks systemd to SIGKILL every process in the mariadb unit.
// Falls back to direct SIGKILL on the pids if systemctl itself fails.
func killMariaDB() {
	slog.Warn("force killing mariadb unit via systemctl kill --signal=SIGKILL")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "systemctl", "kill", "--signal=SIGKILL", "--kill-whom=all", "mariadb")
	if out, err := cmd.CombinedOutput(); err != nil {
		slog.Warn("systemctl kill failed, falling back to direct SIGKILL",
			"error", err, "output", string(out))
		killMariaDBProcessesDirect()
	}
}

func killMariaDBProcessesDirect() {
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
}

// waitForProcessDeath polls until no mariadbd/mysqld processes remain or the
// deadline elapses. Returns true if all processes are gone.
func waitForProcessDeath(timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	for {
		pids := findMariaDBProcessIDs()
		if len(pids) == 0 {
			return true
		}
		if time.Now().After(deadline) {
			slog.Warn("mariadbd processes still alive after deadline",
				"pids", pids, "timeout", timeout)
			return false
		}
		time.Sleep(processDeathPoll)
	}
}

func reclaimMemory() {
	slog.Info("reclaiming memory", "drop_caches_mode", dropCachesMode)

	// Use syscall.Sync to avoid forking during memory pressure.
	syscall.Sync()

	if err := os.WriteFile("/proc/sys/vm/drop_caches", []byte(fmt.Sprintf("%d", dropCachesMode)), 0644); err != nil {
		slog.Warn("failed to drop caches", "error", err)
	} else {
		slog.Info("dropped caches", "mode", dropCachesMode)
	}
}

// startMariaDB clears any failed state and starts mariadb via systemd.
// Returns true only if the unit started AND the daemon is reachable within
// mariadbReachableTimeout.
func startMariaDB(creds MySQLCredentials) bool {
	// Clear any failed state so systemd's start rate limiter does not refuse
	// the start after several recoveries in a row.
	resetCtx, resetCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer resetCancel()
	if out, err := exec.CommandContext(resetCtx, "systemctl", "reset-failed", "mariadb").CombinedOutput(); err != nil {
		slog.Warn("systemctl reset-failed mariadb returned an error",
			"error", err, "output", string(out))
	} else {
		slog.Info("cleared mariadb failed state")
	}

	slog.Info("starting mariadb via systemctl")

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "systemctl", "start", "mariadb")
	output, err := cmd.CombinedOutput()
	if err != nil {
		slog.Error("failed to start mariadb", "error", err, "output", string(output))
		return false
	}

	slog.Info("mariadb started, verifying it becomes reachable")

	deadline := time.Now().Add(mariadbReachableTimeout)
	for time.Now().Before(deadline) {
		if checkReachable(creds) {
			slog.Info("mariadb is reachable after restart")
			return true
		}
		time.Sleep(mariadbReachablePoll)
	}

	slog.Error("mariadb started but is not reachable", "timeout", mariadbReachableTimeout)
	return false
}

// forceSystemReboot triggers an immediate, no-delay reboot of the machine.
// this is the last resort.
// it is called only when normal recovery (kill + start) has failed.
func forceSystemReboot(reason string) {
	slog.Error("HARD REBOOT", "reason", reason)

	syscall.Sync()

	// Make sure sysrq is enabled. Value 1 means "all functions allowed".
	if err := os.WriteFile("/proc/sys/kernel/sysrq", []byte("1"), 0644); err != nil {
		slog.Warn("failed to enable sysrq", "error", err)
	}

	// 'b' = immediate reboot without syncing or unmounting. We already
	// synced above; the kernel will not unmount anything.
	if err := os.WriteFile("/proc/sysrq-trigger", []byte("b"), 0200); err != nil {
		slog.Warn("sysrq reboot trigger failed, falling back to systemctl",
			"error", err)
	} else {
		// On a healthy kernel this line is never reached.
		time.Sleep(2 * time.Second)
	}

	// Fallback 1: systemctl reboot --force --force
	// This skips shutdown scripts and unmounts
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if out, err := exec.CommandContext(ctx, "systemctl", "reboot", "--force", "--force").CombinedOutput(); err != nil {
		slog.Warn("systemctl reboot --force --force failed",
			"error", err, "output", string(out))
	} else {
		time.Sleep(2 * time.Second)
	}

	// Fallback 2: the reboot(2) syscall directly.
	if err := syscall.Reboot(syscall.LINUX_REBOOT_CMD_RESTART); err != nil {
		slog.Error("reboot(2) syscall failed, giving up", "error", err)
	}
}
