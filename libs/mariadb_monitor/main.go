package main

import (
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	if len(os.Args) > 1 {
		slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
			Level: slog.LevelInfo,
		})))

		switch os.Args[1] {
		case "run":
			// fall through to main monitor loop
		case "install":
			if err := install(); err != nil {
				slog.Error("install failed", "error", err)
				os.Exit(1)
			}
			return
		case "uninstall":
			if err := uninstall(); err != nil {
				slog.Error("uninstall failed", "error", err)
				os.Exit(1)
			}
			return
		case "help", "-h", "--help":
			printHelp()
			return
		default:
			fmt.Fprintf(os.Stderr, "Unknown command: %s\n", os.Args[1])
			printHelp()
			os.Exit(1)
		}
	}

	if _, err := os.Stat(configFile); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "config not found, generating default at %s\n", configFile)
		if err := GenerateDefaultConfig(); err != nil {
			fmt.Fprintf(os.Stderr, "WARNING: could not generate default config: %v\n", err)
		}
	}

	cfg, err := LoadConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: failed to load config from %s: %v\n", configFile, err)
		os.Exit(1)
	}

	logWriter, err := setupLogging(cfg.LogLevel)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: failed to set up logging: %v\n", err)
		os.Exit(1)
	}
	defer logWriter.Close()

	creds, err := LoadMySQLCredentials()
	if err != nil {
		slog.Error("failed to load mysql credentials", "path", myCnfPath, "error", err)
		fmt.Fprintf(os.Stderr, "ERROR: %s is required with [client] section for user, password, and socket.\n", myCnfPath)
		os.Exit(1)
	}

	slog.Info("mariadb monitor starting",
		"check_interval", cfg.CheckInterval,
		"window_size", cfg.WindowSize,
		"sustained_ratio", cfg.SustainedRatio,
		"mariadb_socket", creds.Socket,
		"mariadb_user", creds.User,
		"log_level", cfg.LogLevel,
		"log_file", logFile,
		"max_recoveries_per_hour", cfg.MaxRecoveriesPerHour,
		"drop_caches_mode", cfg.DropCachesMode,
	)

	windows := newMetricWindows(cfg.WindowSize)
	cache := &snapshotCache{}

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	ticker := time.NewTicker(cfg.CheckInterval)
	defer ticker.Stop()

	var cooldownUntil time.Time
	checkCount := 0

	for {
		select {
		case sig := <-sigCh:
			slog.Info("received signal, shutting down", "signal", sig)
			return
		case <-ticker.C:
			if time.Now().Before(cooldownUntil) {
				slog.Debug("in cooldown, skipping check", "remaining", time.Until(cooldownUntil).Round(time.Second))
				continue
			}

			checkCount++
			if checkCount%60 == 0 {
				if newCreds, err := LoadMySQLCredentials(); err == nil {
					creds = newCreds
					slog.Debug("reloaded mysql credentials", "user", creds.User, "socket", creds.Socket)
				} else {
					slog.Warn("failed to reload mysql credentials, using cached", "error", err)
				}
			}

			if runCheck(cfg, creds, windows, cache) {
				recoveryTimestamps = append(recoveryTimestamps, time.Now())
				cooldownUntil = time.Now().Add(cfg.CooldownAfterRecovery)
				slog.Info("entering cooldown", "until", cooldownUntil.Format(time.RFC3339))
			}
		}
	}
}

type metricWindows struct {
	psiCPU       MetricWindow
	psiMemory    MetricWindow
	psiIO        MetricWindow
	iowait       MetricWindow
	memUsage     MetricWindow
	swapUsage    MetricWindow
	pageRate     MetricWindow
	memAvailable MetricWindow
	memCached    MetricWindow
	swapFree     MetricWindow
}

func newMetricWindows(size int) *metricWindows {
	return &metricWindows{
		psiCPU:       NewMetricWindow(size),
		psiMemory:    NewMetricWindow(size),
		psiIO:        NewMetricWindow(size),
		iowait:       NewMetricWindow(size),
		memUsage:     NewMetricWindow(size),
		swapUsage:    NewMetricWindow(size),
		pageRate:     NewMetricWindow(size),
		memAvailable: NewMetricWindow(size),
		memCached:    NewMetricWindow(size),
		swapFree:     NewMetricWindow(size),
	}
}

func printHelp() {
	fmt.Println("MariaDB Monitor")
	fmt.Println("")
	fmt.Println("Usage:")
	fmt.Println("  mariadb-monitor [command]")
	fmt.Println("")
	fmt.Println("Commands:")
	fmt.Println("  run        Run the monitor directly (default)")
	fmt.Println("  install    Install the monitor as a systemd service")
	fmt.Println("  uninstall  Remove the monitor systemd service")
	fmt.Println("  help       Show this help message")
	fmt.Println("")
	fmt.Println("When run without arguments, the monitor runs in the foreground.")
}

func runCheck(cfg Config, creds MySQLCredentials, w *metricWindows, cache *snapshotCache) bool {
	frozenCheck := checkMachineFrozen()
	var triggers []string

	if psiCPU, err := checkPSI("cpu"); err == nil {
		w.psiCPU.Push(psiCPU, cfg.PSICPUThreshold)
		slog.Debug("psi_cpu", "avg10", psiCPU)
	} else {
		slog.Warn("failed to check psi cpu", "error", err)
	}

	if psiMem, err := checkPSI("memory"); err == nil {
		w.psiMemory.Push(psiMem, cfg.PSIMemoryThreshold)
		slog.Debug("psi_memory", "avg10", psiMem)
	} else {
		slog.Warn("failed to check psi memory", "error", err)
	}

	if psiIO, err := checkPSI("io"); err == nil {
		w.psiIO.Push(psiIO, cfg.PSIIOThreshold)
		slog.Debug("psi_io", "avg10", psiIO)
	} else {
		slog.Warn("failed to check psi io", "error", err)
	}

	iowaitVal, iowaitErr := checkIOWait(cache)
	if iowaitErr == nil {
		w.iowait.Push(iowaitVal, cfg.IOWaitThreshold)
		slog.Debug("iowait", "percent", fmt.Sprintf("%.1f", iowaitVal))
	} else {
		slog.Warn("failed to check iowait", "error", iowaitErr)
	}

	mem, memErr := checkMemory()
	if memErr == nil {
		w.memUsage.Push(mem.UsagePercent, cfg.MemoryUsageThreshold)
		w.swapUsage.Push(mem.SwapPercent, cfg.SwapUsageThreshold)
		w.memAvailable.Push(float64(mem.MemAvailable), 0)
		w.memCached.Push(float64(mem.Cached), 0)
		w.swapFree.Push(float64(mem.SwapFree), 0)

		slog.Debug("memory",
			"usage_percent", fmt.Sprintf("%.1f", mem.UsagePercent),
			"swap_percent", fmt.Sprintf("%.1f", mem.SwapPercent),
			"mem_available_kb", mem.MemAvailable,
			"cached_kb", mem.Cached,
			"swap_free_kb", mem.SwapFree,
		)
	} else {
		slog.Warn("failed to check memory", "error", memErr)
	}

	pageRateVal, pageRateErr := checkPageRate(cache, cfg.CheckInterval)
	if pageRateErr == nil {
		w.pageRate.Push(pageRateVal, cfg.PageRateThreshold)
		slog.Debug("page_rate", "pages_per_sec", pageRateVal)
	} else {
		slog.Warn("failed to check page rate", "error", pageRateErr)
	}

	if memErr == nil && mem.UsagePercent >= cfg.CriticalMemoryThreshold {
		triggers = append(triggers, fmt.Sprintf("critical_memory=%.1f%%", mem.UsagePercent))
	}

	if iowaitErr == nil && iowaitVal >= cfg.IOWaitThreshold {
		if checkIOFreeze(cfg.IOFreezeTimeout) {
			triggers = append(triggers, "io_freeze")
		}
	}

	if w.psiCPU.IsSustained(cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_cpu")
	}
	if w.psiMemory.IsSustained(cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_memory")
	}
	if w.psiIO.IsSustained(cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_io")
	}
	if w.iowait.IsSustained(cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_iowait")
	}
	if w.memUsage.IsSustained(cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_memory_usage")
	}
	if w.swapUsage.IsSustained(cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_swap_usage")
	}
	if w.pageRate.IsSustained(cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_page_rate")
	}
	
	if isFrozen, reason := checkMachineFrozen(); isFrozen {
		frozenCheck = &frozenState{frozen: true, reason: reason}
		triggers = append(triggers, fmt.Sprintf("machine_frozen(%s)", reason))
	}

	if memErr == nil && mem.SwapTotal > 0 {
		swapFreePercent := float64(mem.SwapFree) / float64(mem.SwapTotal) * 100.0
		if w.memAvailable.Trend() == "falling" &&
			w.memCached.Trend() == "falling" &&
			swapFreePercent < cfg.SwapHeadroom {
			triggers = append(triggers, fmt.Sprintf("predictive_memory_exhaustion(swap_free=%.1f%%)", swapFreePercent))
		}
	}

	logSpikes(cfg, w)

	if len(triggers) == 0 {
		return false
	}

	// sustained_swap_usage alone is not actionable — swap 100% usage can be normal
	// So it requires at least one additional trigger to act.
	if len(triggers) == 1 && triggers[0] == "sustained_swap_usage" {
		slog.Debug("ignoring sole sustained_swap_usage trigger, requires at least one more trigger to act")
		return false
	}

	slog.Warn("pressure detected", "triggers", triggers)

	dbHealth := checkMariaDBHealth(creds)
	if dbHealth.Reachable && !dbHealth.IsStuck {
		slog.Warn("pressure detected but mariadb is healthy, skipping recovery", "triggers", triggers)
		return false
	}

	if cfg.MaxRecoveriesPerHour > 0 && recentRecoveryCount(cfg.MaxRecoveriesPerHour) {
		slog.Error("recovery rate limit reached, skipping",
			"max_per_hour", cfg.MaxRecoveriesPerHour,
			"triggers", triggers,
		)
		return false
	}

	return performRecovery(cfg, triggers, dbHealth, creds, frozenCheck)
}

type frozenState struct {
	frozen bool
	reason string
}

var recoveryTimestamps []time.Time

func recentRecoveryCount(maxPerHour int) bool {
	cutoff := time.Now().Add(-1 * time.Hour)
	var recent []time.Time
	for _, t := range recoveryTimestamps {
		if t.After(cutoff) {
			recent = append(recent, t)
		}
	}
	recoveryTimestamps = recent
	return len(recent) >= maxPerHour
}

func checkMariaDBHealth(creds MySQLCredentials) DBHealth {
	if !checkReachable(creds) {
		slog.Warn("mariadb is unreachable", "socket", creds.Socket, "host", creds.Host, "port", creds.Port)
		return DBHealth{Reachable: false}
	}

	health := checkProcesslist(creds)
	if health.IsStuck {
		slog.Warn("mariadb has stuck queries", "stuck_count", health.StuckQueries, "details", health.Details)
	} else {
		slog.Debug("mariadb processlist is healthy")
	}
	return health
}

func logSpikes(cfg Config, w *metricWindows) {
	type spike struct {
		name   string
		window *MetricWindow
	}
	spikes := []spike{
		{"psi_cpu", &w.psiCPU},
		{"psi_memory", &w.psiMemory},
		{"psi_io", &w.psiIO},
		{"iowait", &w.iowait},
		{"memory_usage", &w.memUsage},
		{"swap_usage", &w.swapUsage},
		{"page_rate", &w.pageRate},
	}
	for _, s := range spikes {
		if s.window.IsSpike(cfg.SustainedRatio) {
			latest := s.window.buf.Latest()
			slog.Info("spike detected (not sustained)",
				"metric", s.name,
				"value", fmt.Sprintf("%.1f", latest.value),
				"trend", s.window.Trend(),
			)
		}
	}
}
