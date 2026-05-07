package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
	"time"
)

// systemdKillWhoFlag is set once at init to the correct flag name for the
// running systemd version. "--kill-whom" was introduced in systemd 252;
// older releases (e.g. Ubuntu 22.04 ships 249) require "--kill-who".
var systemdKillWhoFlag string

func init() {
	systemdKillWhoFlag = detectKillWhoFlag()
	slog.Info("systemd kill flag detected", "flag", systemdKillWhoFlag)
}

func detectKillWhoFlag() string {
	out, err := exec.Command("systemctl", "--version").Output()
	if err != nil {
		return "--kill-who=all" // safe default for older systemd
	}
	// First line is like: "systemd 249 (249.11-...)" or "systemd 254"
	line := strings.SplitN(string(out), "\n", 2)[0]
	fields := strings.Fields(line)
	if len(fields) >= 2 {
		if ver, err := strconv.Atoi(fields[1]); err == nil && ver >= 252 {
			return "--kill-whom=all"
		}
	}
	return "--kill-who=all"
}

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

<<<<<<< HEAD
	killed := false
	if isFrozen {
		slog.Warn("machine appears frozen, skipping graceful stop and killing mariadb directly", "reason", reason)
<<<<<<< HEAD
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
=======
		killMariaDB()
	} else if !stopMariaDB(cfg.Monitor.StopTimeout) {
		killMariaDB()
	}

	reclaimMemory(cfg.Monitor.DropCachesMode)
	startMariaDB(creds)
>>>>>>> d97e09880 (feat(mariadb-monitor): Add auto-trim memory usage)
=======
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
>>>>>>> 1fc1aa4db (feat(mariadb-monitor): Force reboot if db cant be stopped due to stall)

	return true
}

// killMariaDB asks systemd to SIGKILL every process in the mariadb unit.
// Falls back to direct SIGKILL on the pids if systemctl itself fails.
func killMariaDB() {
	slog.Warn("force killing mariadb unit via systemctl kill --signal=SIGKILL")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "systemctl", "kill", "--signal=SIGKILL", systemdKillWhoFlag, "mariadb")
	if out, err := cmd.CombinedOutput(); err != nil {
		slog.Warn("systemctl kill failed, falling back to direct SIGKILL",
			"error", err, "output", string(out))
		killMariaDBProcessesDirect()
	}
}

<<<<<<< HEAD
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
=======
func killMariaDBProcessesDirect() {
	for _, pid := range findMariaDBProcessIDs() {
>>>>>>> 1fc1aa4db (feat(mariadb-monitor): Force reboot if db cant be stopped due to stall)
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
<<<<<<< HEAD

	if allFailed {
		slog.Error("failed to SIGKILL any mariadb process")
		return false
	}

	time.Sleep(2 * time.Second)
	return true
=======
>>>>>>> 1fc1aa4db (feat(mariadb-monitor): Force reboot if db cant be stopped due to stall)
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

<<<<<<< HEAD
func startMariaDB(creds MySQLCredentials) bool {
=======
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

>>>>>>> 1fc1aa4db (feat(mariadb-monitor): Force reboot if db cant be stopped due to stall)
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

<<<<<<< HEAD
	slog.Warn("mariadb started but is not reachable (socket/TCP) after 10s")
	return false
}

func rebootMachine() {
	slog.Error("initiating machine reboot via syscall")
	syscall.Reboot(syscall.LINUX_REBOOT_CMD_RESTART)
=======
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
>>>>>>> 1fc1aa4db (feat(mariadb-monitor): Force reboot if db cant be stopped due to stall)
}
