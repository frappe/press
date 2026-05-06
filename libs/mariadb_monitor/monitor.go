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
}

func newMonitor(cfg Config, creds MySQLCredentials) *Monitor {
	return &Monitor{
		cfg:     cfg,
		creds:   creds,
		windows: newMetricWindows(cfg.WindowSize),
		cache:   &snapshotCache{},
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
		m.cooldownUntil = time.Now().Add(m.cfg.CooldownAfterRecovery)
		slog.Info("entering cooldown", "until", m.cooldownUntil.Format(time.RFC3339))
	}
}

func (m *Monitor) runCheck() CheckOutcome {
	triggers, frozen := m.collectTriggers()

	if len(triggers) == 0 {
		return OutcomeNoAction
	}

	if len(triggers) == 1 && triggers[0] == "sustained_swap_usage" {
		slog.Debug("ignoring sole sustained_swap_usage trigger")
		return OutcomeNoAction
	}

	slog.Warn("pressure detected", "triggers", triggers)

	dbHealth := checkMariaDBHealth(m.cfg, m.creds)
	if dbHealth.Reachable && !dbHealth.IsStuck {
		slog.Warn("pressure detected but mariadb is healthy, skipping recovery", "triggers", triggers)
		return OutcomeNoAction
	}

	if m.recentRecoveryCount() {
		slog.Error("recovery rate limit reached, skipping",
			"max_per_hour", m.cfg.MaxRecoveriesPerHour,
			"triggers", triggers,
		)
		return OutcomeNoAction
	}

	if performRecovery(m.cfg, triggers, dbHealth, m.creds, frozen) {
		return OutcomeRecovered
	}
	return OutcomeNoAction
}

func (m *Monitor) recentRecoveryCount() bool {
	cutoff := time.Now().Add(-time.Hour)
	var recent []time.Time
	for _, t := range m.recoveryTimestamps {
		if t.After(cutoff) {
			recent = append(recent, t)
		}
	}
	m.recoveryTimestamps = recent
	if m.cfg.MaxRecoveriesPerHour <= 0 {
		return false
	}
	return len(recent) >= m.cfg.MaxRecoveriesPerHour
}
