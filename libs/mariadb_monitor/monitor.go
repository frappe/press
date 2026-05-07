package main

import (
	"log/slog"
	"os"
	"time"
)

type CheckOutcome int

const (
	OutcomeNoAction CheckOutcome = iota
	OutcomeRecovered
)

type Monitor struct {
	cfg                Config
	creds              MySQLCredentials
	windows            *metricWindows
	cache              *snapshotCache
	cooldownUntil      time.Time
	checkCount         int
	recoveryTimestamps []time.Time

	lastCgroupHighEvents   uint64
	lastCgroupMaxEvents    uint64
	memHighHitsConsecutive int
	lastReleaseAt          time.Time

	innoDBBufferPreReduction uint64
	preReductionRSS          uint64
}

func newMonitor(cfg Config, creds MySQLCredentials) *Monitor {
	// Snapshot cgroup event counters so the first tick computes a delta.
	initCgroup := readCgroupMemory()
	return &Monitor{
		cfg:                  cfg,
		creds:                creds,
		windows:              newMetricWindows(cfg.Monitor.WindowSize),
		cache:                &snapshotCache{},
		lastCgroupHighEvents: initCgroup.HighEvents,
		lastCgroupMaxEvents:  initCgroup.MaxEvents,
	}
}

func (m *Monitor) run(sigCh <-chan os.Signal) {
	ticker := time.NewTicker(m.cfg.CheckInterval)
	defer ticker.Stop()

	for {
		select {
		case sig := <-sigCh:
			slog.Info("received signal, shutting down", "signal", sig)
			return
		case <-ticker.C:
			m.tick()
		}
	}
}

func (m *Monitor) tick() {
	if time.Now().Before(m.cooldownUntil) {
		slog.Debug("in cooldown, skipping check", "remaining", time.Until(m.cooldownUntil).Round(time.Second))
		return
	}

	m.checkCount++
	if m.checkCount%60 == 0 {
		if newCreds, err := LoadMySQLCredentials(); err == nil {
			m.creds = newCreds
			slog.Debug("reloaded mysql credentials", "user", m.creds.User, "socket", m.creds.Socket)
		} else {
			slog.Warn("failed to reload mysql credentials, using cached", "error", err)
		}
	}

	if outcome := m.runCheck(); outcome == OutcomeRecovered {
		m.recoveryTimestamps = append(m.recoveryTimestamps, time.Now())
		m.cooldownUntil = time.Now().Add(m.cfg.Monitor.CooldownAfterRecovery)
		slog.Info("entering cooldown", "until", m.cooldownUntil.Format(time.RFC3339))
	}
}

func (m *Monitor) shouldAttemptMemoryRelease() bool {
	if !m.cfg.Release.Enabled {
		return false
	}
	if !m.lastReleaseAt.IsZero() && time.Since(m.lastReleaseAt) < m.cfg.Release.Cooldown {
		slog.Debug("memory release in cooldown", "remaining", (m.cfg.Release.Cooldown - time.Since(m.lastReleaseAt)).Round(time.Second))
		return false
	}
	// PSI memory rising above the relief threshold.
	psiLatest := m.windows.psiMemory.buf.Latest()
	if m.windows.psiMemory.Trend() == "rising" && psiLatest.value >= m.cfg.Release.PSIMemoryThreshold {
		slog.Info("memory release trigger: PSI memory rising", "avg10", psiLatest.value)
		return true
	}
	// Sustained cgroup memory.high or memory.max events.
	if m.memHighHitsConsecutive >= m.cfg.Release.MemHighThreshold {
		slog.Info("memory release trigger: cgroup pressure events", "consecutive_ticks", m.memHighHitsConsecutive)
		return true
	}
	return false
}

func (m *Monitor) runCheck() CheckOutcome {
	m.tryRestoreInnoDBBuffer()

	triggers, frozen := m.collectTriggers()

	// Try soft relief before considering a restart.
	if m.shouldAttemptMemoryRelease() {
		_, originalSize := tryRelieveMemoryPressure(m.cfg, m.creds)
		m.lastReleaseAt = time.Now()
		m.memHighHitsConsecutive = 0
		if originalSize > 0 {
			m.innoDBBufferPreReduction = originalSize
			m.preReductionRSS = readCgroupMemory().CurrentUsage
		}
	}

	if len(triggers) == 0 {
		return OutcomeNoAction
	}

	slog.Warn("pressure detected", "triggers", triggers)

	dbHealth := checkMariaDBHealth(m.cfg, m.creds)
	if dbHealth.Reachable && !dbHealth.IsStuck {
		slog.Warn("pressure detected but mariadb is healthy, skipping recovery", "triggers", triggers)
		return OutcomeNoAction
	}

	if m.isRecoveryRateLimited() {
		slog.Error("recovery rate limit reached, skipping",
			"max_per_hour", m.cfg.Monitor.MaxRecoveriesPerHour,
			"triggers", triggers,
		)
		return OutcomeNoAction
	}

	if performRecovery(m.cfg, triggers, dbHealth, m.creds, frozen) {
		return OutcomeRecovered
	}
	return OutcomeNoAction
}

// tryRestoreInnoDBBuffer restores the InnoDB buffer pool to its pre-reduction
// size once the process RSS (cgroup memory.current) has fallen below the
// level it was at when the reduction was made.
func (m *Monitor) tryRestoreInnoDBBuffer() {
	if m.innoDBBufferPreReduction == 0 {
		return
	}
	cg := readCgroupMemory()
	if cg.CurrentUsage >= m.preReductionRSS {
		slog.Debug("waiting for RSS to drop before restoring InnoDB buffer pool",
			"rss_now_mb", cg.CurrentUsage/1024/1024,
			"rss_at_reduction_mb", m.preReductionRSS/1024/1024,
		)
		return
	}
	db := NewDatabase(m.creds)
	actual, err := db.ResizeInnoDBBufferPool(m.innoDBBufferPreReduction)
	if err != nil {
		slog.Warn("failed to restore InnoDB buffer pool after RSS drop",
			"error", err,
			"target_mb", m.innoDBBufferPreReduction/1024/1024,
		)
		return
	}
	slog.Info("restored InnoDB buffer pool after RSS went down",
		"to_mb", actual/1024/1024,
		"rss_previous_mb", m.preReductionRSS/1024/1024,
		"rss_now_mb", cg.CurrentUsage/1024/1024,
	)
	m.innoDBBufferPreReduction = 0
	m.preReductionRSS = 0
}

// isRecoveryRateLimited returns true if the number of recent recoveries has
// reached the configured hourly maximum.
func (m *Monitor) isRecoveryRateLimited() bool {
	cutoff := time.Now().Add(-time.Hour)
	var recent []time.Time
	for _, t := range m.recoveryTimestamps {
		if t.After(cutoff) {
			recent = append(recent, t)
		}
	}
	m.recoveryTimestamps = recent
	if m.cfg.Monitor.MaxRecoveriesPerHour <= 0 {
		return false
	}
	return len(recent) >= m.cfg.Monitor.MaxRecoveriesPerHour
}
