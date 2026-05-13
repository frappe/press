package main

import (
	"fmt"
	"log/slog"
	"os"
	"strings"
	"time"
)

type Monitor struct {
	cfg        Config
	creds      MySQLCredentials
	db         *Database
	windows    *metricWindows
	cache      *snapshotCache
	checkCount int

	lastCgroupHighEvents   uint64
	lastCgroupMaxEvents    uint64
	memHighHitsConsecutive int
	lastReleaseAt          time.Time
	lastCoredumpAt         time.Time
	lastRecoveryAt         time.Time

	innoDBBufferPreReduction uint64
	preReductionRSS          uint64
	lastBufferShrinkAt       time.Time

	// Dedupe state for the "pressure detected but mariadb is healthy" log
	// to avoid spamming on sustained background load.
	lastSkipTriggers string
	lastSkipLoggedAt time.Time

	// Dedupe for the restore-headroom deferral warn.
	lastRestoreDeferLogAt time.Time

	// cgroupMemLowSince tracks when the MariaDB cgroup available memory
	// first dropped below cgroupMemAvailLowMB. Zero means it is healthy.
	cgroupMemLowSince time.Time

	// cgroupEmergencyLastRelease tracks the last soft release attempt.
	// Rate-limited to once every cgroupEmergencyReleaseCooldown.
	cgroupEmergencyLastRelease time.Time

	// Async recovery state: performRecovery runs in a goroutine so the tick loop
	// keeps running. Only the main goroutine reads/writes these fields.
	recoveryDone            chan recoveryOutcome // non-nil while a recovery worker is running
	recoveryStartedAt       time.Time
	lastRecoveryProgressLog time.Time
}

// recoveryOutcome carries the worker goroutine's result back to tick().
type recoveryOutcome struct {
	success        bool
	wantedCoredump bool
	critical       bool
}

const (
	skipTriggerLogMinInterval   = 60 * time.Second
	recoveryProgressLogInterval = 30 * time.Second
)

func newMonitor(cfg Config, creds MySQLCredentials) *Monitor {
	// Snapshot cgroup event counters so the first tick computes a delta.
	initCgroup := readCgroupMemory()
	m := &Monitor{
		cfg:                  cfg,
		creds:                creds,
		db:                   NewDatabase(creds),
		windows:              newMetricWindows(cfg.Monitor.WindowSize),
		cache:                &snapshotCache{},
		lastCgroupHighEvents: initCgroup.HighEvents,
		lastCgroupMaxEvents:  initCgroup.MaxEvents,
	}
	m.recoverBufferReductionState()
	return m
}

// recoverBufferReductionState detects a prior unrestored buffer shrink.
// Pre-loads innoDBBufferPreReduction so restoration resumes automatically.
func (m *Monitor) recoverBufferReductionState() {
	configuredSize := ReadConfiguredBufferPoolSize()
	if configuredSize == 0 {
		// No innodb_buffer_pool_size found in .cnf files, nothing to compare.
		return
	}

	bpCfg, err := m.db.GetInnoDBBufferPoolConfig()
	if err != nil {
		slog.Warn("startup: could not read live InnoDB buffer pool size, skipping restore check", "error", err)
		return
	}

	if bpCfg.Size >= configuredSize {
		// Pool is at or above the configured value, nothing to restore.
		return
	}

	slog.Warn("startup: InnoDB buffer pool is smaller than configured size, resuming restoration",
		"live_mb", bpCfg.Size/1024/1024,
		"configured_mb", configuredSize/1024/1024,
	)
	m.innoDBBufferPreReduction = configuredSize
	// preReductionRSS is left at 0; the RSS guard is skipped in tryRestoreInnoDBBuffer.
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
	m.checkCount++
	if m.checkCount%60 == 0 {
		if newCreds, err := LoadMySQLCredentials(); err == nil {
			m.creds = newCreds
			m.db.Close()
			m.db = NewDatabase(newCreds)
			slog.Debug("reloaded mysql credentials", "user", m.creds.User, "socket", m.creds.Socket)
		} else {
			slog.Warn("failed to reload mysql credentials, using cached", "error", err)
		}
	}

	// Recovery is async: while the worker is running, skip the tick.
	if m.recoveryDone != nil {
		select {
		case res := <-m.recoveryDone:
			m.recoveryDone = nil
			m.handleRecoveryCompletion(res)
		default:
			if time.Since(m.lastRecoveryProgressLog) >= recoveryProgressLogInterval {
				slog.Warn("recovery still in progress",
					"elapsed", time.Since(m.recoveryStartedAt).Round(time.Second),
					"reachable_timeout", mariadbReachableTimeout,
				)
				m.lastRecoveryProgressLog = time.Now()
			}
			return
		}
	}

	m.runCheck()
}

func hasCriticalMemory(triggers []string) bool {
	for _, t := range triggers {
		if strings.HasPrefix(t, "critical_memory=") {
			return true
		}
	}
	return false
}

func (m *Monitor) shouldAttemptMemoryRelease(hasTriggers, critical bool) bool {
	if !m.cfg.Release.Enabled {
		return false
	}
	if critical {
		slog.Warn("memory release trigger: critical memory, bypassing cooldown")
		return true
	}
	// Cgroup headroom check bypasses the cooldown: keep acting every tick
	// while headroom is below the soft threshold.
	cg := readCgroupMemory()
	cgCeiling := cg.MemoryHigh
	if cgCeiling == 0 {
		cgCeiling = cg.MemoryMax
	}
	if cgCeiling > 0 && cg.CurrentUsage > 0 {
		var cgAvailMB int64
		if cg.CurrentUsage < cgCeiling {
			cgAvailMB = int64(cgCeiling-cg.CurrentUsage) / 1024 / 1024
		}
		if cgAvailMB < cgroupMemSoftLowMB {
			slog.Info("memory release trigger: cgroup headroom low, bypassing cooldown",
				"avail_mb", cgAvailMB,
				"ceiling_mb", int64(cgCeiling)/1024/1024,
				"soft_threshold_mb", cgroupMemSoftLowMB,
			)
			return true
		}
	}
	if !m.lastReleaseAt.IsZero() && time.Since(m.lastReleaseAt) < m.cfg.Release.Cooldown {
		slog.Debug("memory release in cooldown",
			"remaining", (m.cfg.Release.Cooldown - time.Since(m.lastReleaseAt)).Round(time.Second),
		)
		return false
	}
	if hasTriggers {
		mem, err := checkMemory()
		if err != nil {
			return false
		}
		availableMB := mem.MemAvailable / 1024
		if availableMB >= m.cfg.Release.MinFreeMB {
			slog.Debug("memory release skipped: memory sufficient despite triggers",
				"available_mb", availableMB,
				"min_free_mb", m.cfg.Release.MinFreeMB,
			)
			return false
		}
		slog.Info("memory release trigger: system pressure with low memory",
			"available_mb", availableMB,
			"min_free_mb", m.cfg.Release.MinFreeMB,
		)
		return true
	}
	psiLatest := m.windows.psiMemory.buf.Latest()
	if m.windows.psiMemory.Trend() == "rising" && psiLatest.value >= m.cfg.Release.PSIMemoryThreshold {
		slog.Info("memory release trigger: PSI memory rising", "avg60", psiLatest.value)
		return true
	}
	if m.memHighHitsConsecutive >= m.cfg.Release.MemHighThreshold {
		slog.Info("memory release trigger: cgroup pressure events", "consecutive_ticks", m.memHighHitsConsecutive)
		return true
	}
	return false
}

func (m *Monitor) runCheck() {
	m.tryRestoreInnoDBBuffer()

	triggers, frozen := m.collectTriggers()

	// Detect MariaDB cgroup OOM risk: if available memory stays below
	// cgroupMemAvailLowMB for cgroupMemAvailLowDuration, the DB is frozen.
	oomRisk := m.checkCgroupMemAvail()

	// Always probe DB health even when system metrics look fine. A metadata
	// lock storm can hang the DB without moving PSI/iowait.
	dbHealth := checkMariaDBHealth(m.cfg, m.creds, m.db)
	if oomRisk {
		dbHealth.IsStuck = true
		triggers = append(triggers, "cgroup_oom_risk")
	}
	if dbHealth.IsStuck {
		if dbHealth.ExternallyUnhealthy {
			triggers = append(triggers, "external_healthcheck=unhealthy")
		}
		if dbHealth.StuckQueries > 0 {
			triggers = append(triggers, fmt.Sprintf("stuck_queries=%d", dbHealth.StuckQueries))
		}
	}

	hasTriggers := len(triggers) > 0
	critical := hasCriticalMemory(triggers)

	// At critical memory, kill non-essential processes first. The DB is
	// often the victim of memory pressure from something else.
	if critical && len(m.cfg.Release.KillableProcesses) > 0 {
		if killed := killProcessesByName(m.cfg.Release.KillableProcesses); killed > 0 {
			if mem, err := checkMemory(); err == nil &&
				mem.UsagePercent < m.cfg.Thresholds.CriticalMemoryThreshold {
				slog.Warn("memory recovered after killing non-essential processes, skipping db recovery",
					"killed", killed,
					"usage_percent", fmt.Sprintf("%.1f", mem.UsagePercent),
				)
				return
			}
			slog.Warn("killed non-essential processes but memory still critical, proceeding with db recovery",
				"killed", killed,
			)
		}
	}

	// At critical memory, skip soft release entirely. Under OOM the DB
	// queries hang and burn time before the kill. Go straight to recovery.
	if !critical && m.shouldAttemptMemoryRelease(hasTriggers, critical) {
		rssBefore := readCgroupMemory().CurrentUsage
		_, originalSize := tryRelieveMemoryPressure(m.cfg, m.db)
		m.lastReleaseAt = time.Now()
		m.memHighHitsConsecutive = 0
		if originalSize > 0 && m.innoDBBufferPreReduction == 0 {
			m.innoDBBufferPreReduction = originalSize
			m.preReductionRSS = rssBefore
			m.lastBufferShrinkAt = time.Now()
		}
	}

	if !hasTriggers {
		return
	}

	// Note: "pressure detected" is logged at DEBUG only. We log at WARN
	// only when it leads to action, to avoid flooding logs on sustained load.
	slog.Debug("pressure detected", "triggers", triggers)

	if dbHealth.Reachable && !dbHealth.IsStuck && !critical {
		m.logHealthySkip(triggers)
		return
	}

	const minRecoveryGap = 60 * time.Second
	if !m.lastRecoveryAt.IsZero() && time.Since(m.lastRecoveryAt) < minRecoveryGap {
		slog.Warn("recovery rate-limited",
			"next_in", (minRecoveryGap - time.Since(m.lastRecoveryAt)).Round(time.Second),
			"triggers", triggers,
		)
		return
	}

	// Skip coredump under critical memory: gcore roughly doubles RSS while
	// dumping (it reads the full address space) and will OOM the host.
	wantCoredump := shouldTakeCoredump(m.cfg) && !critical &&
		time.Since(m.lastCoredumpAt) >= m.cfg.Coredump.Cooldown

	m.startRecovery(triggers, dbHealth, frozen, wantCoredump, critical)
}

// startRecovery hands recovery off to a goroutine and returns immediately.
// lastRecoveryAt is stamped now so the in-flight period counts toward the rate-limit.
func (m *Monitor) startRecovery(triggers []string, dbHealth DBHealth, frozen *frozenState, wantCoredump, critical bool) {
	now := time.Now()
	m.recoveryStartedAt = now
	m.lastRecoveryProgressLog = now
	m.lastRecoveryAt = now
	if wantCoredump {
		m.lastCoredumpAt = now
	}

	done := make(chan recoveryOutcome, 1)
	m.recoveryDone = done

	// Snapshot what the worker reads. cfg and creds are value-copied;
	// triggers is dup'd so a future tick cannot race with logging.
	cfg := m.cfg
	creds := m.creds
	triggersCopy := append([]string(nil), triggers...)

	go func() {
		ok := performRecovery(cfg, triggersCopy, dbHealth, creds, frozen, wantCoredump)
		done <- recoveryOutcome{
			success:        ok,
			wantedCoredump: wantCoredump,
			critical:       critical,
		}
	}()
}

// handleRecoveryCompletion runs in the tick goroutine after the worker sends
// its outcome. All Monitor field writes happen here, never in the worker.
func (m *Monitor) handleRecoveryCompletion(res recoveryOutcome) {
	elapsed := time.Since(m.recoveryStartedAt).Round(time.Second)
	if res.success {
		slog.Warn("recovery completed", "elapsed", elapsed)
	} else {
		slog.Error("recovery worker returned without success after reboot attempt", "elapsed", elapsed)
	}

	m.resetCgroupStateAfterRecovery()

	// Last resort: if a fresh mariadbd still can't recover, pressure is external.
	// Reboot is the only deterministic fix.
	if res.critical {
		m.rebootIfStillCritical()
	}
}

// logHealthySkip emits the "pressure detected but mariadb is healthy" warning
// at most once per skipTriggerLogMinInterval for an identical trigger set.
func (m *Monitor) logHealthySkip(triggers []string) {
	key := strings.Join(triggers, ",")
	if key == m.lastSkipTriggers && time.Since(m.lastSkipLoggedAt) < skipTriggerLogMinInterval {
		return
	}
	slog.Warn("pressure detected but mariadb is healthy, skipping recovery", "triggers", triggers)
	m.lastSkipTriggers = key
	m.lastSkipLoggedAt = time.Now()
}

// resetCgroupStateAfterRecovery re-baselines cgroup counters after recovery.
// systemd recreates the cgroup, resetting memory.events to 0.
func (m *Monitor) resetCgroupStateAfterRecovery() {
	cg := readCgroupMemory()
	m.lastCgroupHighEvents = cg.HighEvents
	m.lastCgroupMaxEvents = cg.MaxEvents
	m.memHighHitsConsecutive = 0
	m.innoDBBufferPreReduction = 0
	m.preReductionRSS = 0
	// Reset cgroup low-memory timer so the post-recovery tick does not
	// inherit elapsed time from before recovery and skip the 30s grace period.
	m.cgroupMemLowSince = time.Time{}
	m.cgroupEmergencyLastRelease = time.Time{}
}

// rebootIfStillCritical is the final escalation: if memory is still critical
// after kill+restart, try one more process kill then hard-reboot.
func (m *Monitor) rebootIfStillCritical() {
	// Brief settling window: page cache drops and process exits take a
	// few hundred ms to be reflected in /proc/meminfo.
	time.Sleep(2 * time.Second)

	mem, err := checkMemory()
	if err != nil {
		slog.Warn("post-recovery memory check failed, assuming healthy", "error", err)
		return
	}
	if mem.UsagePercent < m.cfg.Thresholds.CriticalMemoryThreshold {
		slog.Info("post-recovery memory healthy",
			"usage_percent", fmt.Sprintf("%.1f", mem.UsagePercent),
		)
		return
	}

	slog.Error("post-recovery memory still critical, attempting one more non-essential kill",
		"usage_percent", fmt.Sprintf("%.1f", mem.UsagePercent),
		"threshold", m.cfg.Thresholds.CriticalMemoryThreshold,
	)

	if len(m.cfg.Release.KillableProcesses) > 0 {
		killProcessesByName(m.cfg.Release.KillableProcesses)
		time.Sleep(2 * time.Second)
		if mem2, err := checkMemory(); err == nil &&
			mem2.UsagePercent < m.cfg.Thresholds.CriticalMemoryThreshold {
			slog.Warn("memory recovered after final non-essential kill",
				"usage_percent", fmt.Sprintf("%.1f", mem2.UsagePercent),
			)
			return
		}
	}

	slog.Error("memory remains critical after db recovery and non-essential kills, hard-rebooting")
	forceSystemReboot("post_recovery_memory_still_critical")
}

// minBufferRestoreGracePeriod is the wait after a shrink before restoring.
// Prevents shrink-restore thrashing within a single tick cycle.
const minBufferRestoreGracePeriod = 60 * time.Second

// cgroupMemAvailLowMB is the threshold below which the MariaDB cgroup is
// considered memory-starved. New connections fail and queries OOM-abort.
const cgroupMemAvailLowMB = 5

// cgroupMemSoftLowMB is the proactive headroom threshold: trigger a soft release
// before the hard emergency path fires at cgroupMemAvailLowMB.
const cgroupMemSoftLowMB = 100

// cgroupMemAvailLowDuration is how long the cgroup must remain below
// cgroupMemAvailLowMB before we declare the DB unhealthy and trigger recovery.
const cgroupMemAvailLowDuration = 30 * time.Second

// cgroupEmergencyReleaseCooldown is the minimum interval between soft-release
// attempts during cgroup starvation.
const cgroupEmergencyReleaseCooldown = 10 * time.Second

// checkCgroupMemAvail returns true when the MariaDB cgroup has been below
// cgroupMemAvailLowMB for at least cgroupMemAvailLowDuration.
func (m *Monitor) checkCgroupMemAvail() bool {
	cg := readCgroupMemory()

	// "Available" = memory.high − memory.current. Falls back to memory.max
	// when memory.high is unset ("max").
	ceiling := cg.MemoryHigh
	if ceiling == 0 {
		ceiling = cg.MemoryMax
	}
	if ceiling == 0 || cg.CurrentUsage == 0 {
		m.cgroupMemLowSince = time.Time{}
		return false
	}

	var availBytes int64
	if cg.CurrentUsage >= ceiling {
		availBytes = 0
	} else {
		availBytes = int64(ceiling - cg.CurrentUsage)
	}
	availMB := availBytes / 1024 / 1024

	if availMB >= cgroupMemAvailLowMB {
		if !m.cgroupMemLowSince.IsZero() {
			slog.Info("MariaDB cgroup memory recovered",
				"avail_mb", availMB,
				"ceiling_mb", ceiling/1024/1024,
			)
		}
		m.cgroupMemLowSince = time.Time{}
		return false
	}

	if m.cgroupMemLowSince.IsZero() {
		slog.Warn("MariaDB cgroup available memory critically low",
			"avail_mb", availMB,
			"ceiling_mb", ceiling/1024/1024,
			"threshold_mb", cgroupMemAvailLowMB,
		)
		m.cgroupMemLowSince = time.Now()
	}

	// Attempt soft release before declaring DB unhealthy; tcmalloc/InnoDB
	// shrink can free memory even when the cgroup is nearly exhausted.
	if m.cgroupEmergencyLastRelease.IsZero() || time.Since(m.cgroupEmergencyLastRelease) >= cgroupEmergencyReleaseCooldown {
		m.tryCgroupEmergencySoftRelease(cg, ceiling)
		m.cgroupEmergencyLastRelease = time.Now()
	}

	elapsed := time.Since(m.cgroupMemLowSince)
	if elapsed >= cgroupMemAvailLowDuration {
		slog.Error("MariaDB cgroup starved: DB assumed unhealthy",
			"avail_mb", availMB,
			"ceiling_mb", ceiling/1024/1024,
			"duration_s", elapsed.Round(time.Second),
		)
		return true
	}

	slog.Debug("MariaDB cgroup memory low, waiting before declaring unhealthy",
		"avail_mb", availMB,
		"elapsed_s", elapsed.Round(time.Second),
		"threshold_s", cgroupMemAvailLowDuration,
	)
	return false
}

// tryCgroupEmergencySoftRelease runs tcmalloc release + InnoDB buffer shrink
// when cgroup headroom drops below cgroupMemAvailLowMB.
func (m *Monitor) tryCgroupEmergencySoftRelease(cg CgroupMemory, ceiling uint64) {
	slog.Warn("cgroup starvation: attempting emergency soft release (tcmalloc + InnoDB shrink)")

	usageBefore := cg.CurrentUsage
	if releaseTcmalloc(m.cfg, m.db) {
		slog.Warn("cgroup emergency: tcmalloc released pages to OS")
	}

	bpCfg, err := m.db.GetInnoDBBufferPoolConfig()
	if err != nil {
		slog.Warn("cgroup emergency: failed to read buffer pool config", "error", err)
		return
	}
	if bpCfg.ResizePending {
		slog.Debug("cgroup emergency: InnoDB buffer pool resize already in progress, skipping shrink")
		return
	}

	chunkSize := bpCfg.ChunkSize
	if chunkSize == 0 {
		chunkSize = 128 << 20 // 128 MiB default
	}
	instances := bpCfg.Instances
	if instances == 0 {
		instances = 1
	}
	unit := chunkSize * instances
	minBufBytes := m.cfg.Release.InnoDBBufferMinMB * 1024 * 1024
	minBufBytes = ((minBufBytes + unit - 1) / unit) * unit

	cg = readCgroupMemory()

	var freedByTcmalloc uint64
	if usageBefore > cg.CurrentUsage {
		freedByTcmalloc = usageBefore - cg.CurrentUsage
	}

	// Skip InnoDB shrink only if tcmalloc freed ≥2 chunks AND usage is now
	// below ceiling; a small release (5-10 MB) is not enough to skip.
	if cg.CurrentUsage < ceiling && freedByTcmalloc >= 2*unit {
		slog.Info("cgroup emergency: tcmalloc freed sufficient memory, skipping InnoDB shrink",
			"freed_mb", freedByTcmalloc/1024/1024,
			"threshold_mb", 2*unit/1024/1024,
		)
		return
	}

	currentSize := bpCfg.Size
	if currentSize <= minBufBytes {
		slog.Debug("cgroup emergency: InnoDB buffer already at minimum, cannot shrink further",
			"current_mb", currentSize/1024/1024,
			"min_mb", minBufBytes/1024/1024,
		)
		return
	}

	headroom := ceiling / 20 // 5% of ceiling
	var deficit uint64
	if cg.CurrentUsage > ceiling {
		deficit = cg.CurrentUsage - ceiling + headroom
	} else {
		// usage < ceiling but tcmalloc release was too small; use headroom as deficit
		deficit = headroom
	}

	targetSize := uint64(0)
	if deficit >= currentSize {
		targetSize = minBufBytes
	} else {
		targetSize = currentSize - deficit
		if targetSize < minBufBytes {
			targetSize = minBufBytes
		}
	}

	if targetSize >= currentSize {
		return
	}

	actual, err := m.db.ResizeInnoDBBufferPool(targetSize)
	if err != nil {
		slog.Warn("cgroup emergency: InnoDB shrink failed", "error", err,
			"current_mb", currentSize/1024/1024,
			"target_mb", targetSize/1024/1024,
		)
		return
	}
	slog.Warn("cgroup emergency: shrank InnoDB buffer pool",
		"from_mb", currentSize/1024/1024,
		"to_mb", actual/1024/1024,
		"deficit_mb", deficit/1024/1024,
	)
	m.lastReleaseAt = time.Now()
	if m.innoDBBufferPreReduction == 0 {
		m.innoDBBufferPreReduction = currentSize
		m.preReductionRSS = cg.CurrentUsage
		m.lastBufferShrinkAt = time.Now()
	}
}

// releaseTcmallocIfChunkAvailable releases exactly minBytes from tcmalloc
// if its free pool is large enough. Returns true when a release occurred.
func (m *Monitor) releaseTcmallocIfChunkAvailable(minBytes uint64) bool {
	freeBytes, err := m.db.Tcmalloc.FreeBytes()
	if err != nil {
		return false
	}
	if freeBytes <= 0 || uint64(freeBytes) < minBytes {
		slog.Debug("tcmalloc pre-release skipped: insufficient free bytes",
			"free_mb", freeBytes/1024/1024,
			"needed_mb", minBytes/1024/1024,
		)
		return false
	}
	released, err := m.db.Tcmalloc.ReleaseBytes(int64(minBytes))
	if err != nil || released <= 0 {
		return false
	}
	slog.Info("pre-released tcmalloc to make room for InnoDB buffer restore",
		"requested_mb", minBytes/1024/1024,
		"released_mb", released/1024/1024,
		"was_free_mb", freeBytes/1024/1024,
	)
	return true
}

// tryRestoreInnoDBBuffer incrementally grows the InnoDB buffer pool back to
// its pre-reduction target, one chunk at a time, subject to headroom.
func (m *Monitor) tryRestoreInnoDBBuffer() {
	if m.innoDBBufferPreReduction == 0 {
		return
	}

	const bufferRestoreCooldown = 60 * time.Second
	if !m.lastBufferShrinkAt.IsZero() && time.Since(m.lastBufferShrinkAt) < bufferRestoreCooldown {
		return
	}

	// RSS guard: skipped for startup recovery (preReductionRSS == 0).
	cg := readCgroupMemory()
	if m.preReductionRSS != 0 && cg.CurrentUsage >= m.preReductionRSS {
		slog.Debug("waiting for RSS to drop before restoring InnoDB buffer pool",
			"rss_now_mb", cg.CurrentUsage/1024/1024,
			"rss_at_reduction_mb", m.preReductionRSS/1024/1024,
		)
		return
	}

	bpCfg, err := m.db.GetInnoDBBufferPoolConfig()
	if err != nil {
		slog.Warn("tryRestoreInnoDBBuffer: failed to get buffer pool config", "error", err)
		return
	}
	if bpCfg.ResizePending {
		slog.Debug("InnoDB buffer pool resize still in progress, deferring restore")
		return
	}

	currentSize := bpCfg.Size
	if currentSize >= m.innoDBBufferPreReduction {
		m.innoDBBufferPreReduction = 0
		m.preReductionRSS = 0
		return
	}

	chunkSize := bpCfg.ChunkSize
	if chunkSize == 0 {
		chunkSize = 128 << 20 // 128 MiB default
	}
	instances := bpCfg.Instances
	if instances == 0 {
		instances = 1
	}
	unit := chunkSize * instances

	// Use cgroup headroom (memory.high - current) as the available budget.
	cgCeiling := cg.MemoryHigh
	if cgCeiling == 0 {
		cgCeiling = cg.MemoryMax
	}

	var headroomBytes uint64
	if cgCeiling == 0 {
		// No cgroup limit configured; fall back to system-wide free memory.
		mem, err := checkMemory()
		if err != nil {
			return
		}
		availableBytes := mem.MemAvailable * 1024
		minFreeBytes := m.cfg.Release.MinFreeMB * 1024 * 1024
		if availableBytes <= minFreeBytes {
			m.releaseTcmallocIfChunkAvailable(unit)
			if time.Since(m.lastRestoreDeferLogAt) >= skipTriggerLogMinInterval {
				slog.Warn("deferring InnoDB buffer pool restore: no system headroom",
					"available_mb", mem.MemAvailable/1024,
					"min_free_mb", m.cfg.Release.MinFreeMB,
					"target_mb", m.innoDBBufferPreReduction/1024/1024,
				)
				m.lastRestoreDeferLogAt = time.Now()
			}
			return
		}
		headroomBytes = availableBytes - minFreeBytes
	} else {
		// Keep a 5% safety margin below memory.high so a restore attempt
		// does not immediately re-trigger cgroup throttling.
		safetyMargin := cgCeiling / 20
		if cg.CurrentUsage+safetyMargin >= cgCeiling {
			m.releaseTcmallocIfChunkAvailable(unit)
			if time.Since(m.lastRestoreDeferLogAt) >= skipTriggerLogMinInterval {
				slog.Warn("deferring InnoDB buffer pool restore: insufficient cgroup headroom",
					"cgroup_avail_mb", (cgCeiling-cg.CurrentUsage)/1024/1024,
					"safety_margin_mb", safetyMargin/1024/1024,
					"ceiling_mb", cgCeiling/1024/1024,
					"target_mb", m.innoDBBufferPreReduction/1024/1024,
				)
				m.lastRestoreDeferLogAt = time.Now()
			}
			return
		}
		headroomBytes = cgCeiling - cg.CurrentUsage - safetyMargin
	}

	fullRestoreCost := m.innoDBBufferPreReduction - currentSize

	var targetSize uint64
	if headroomBytes >= fullRestoreCost {
		targetSize = m.innoDBBufferPreReduction
	} else {
		units := headroomBytes / unit
		if units == 0 {
			m.releaseTcmallocIfChunkAvailable(unit)
			if time.Since(m.lastRestoreDeferLogAt) >= skipTriggerLogMinInterval {
				slog.Warn("deferring InnoDB buffer pool restore: insufficient headroom for one chunk",
					"headroom_mb", headroomBytes/1024/1024,
					"chunk_mb", unit/1024/1024,
					"target_mb", m.innoDBBufferPreReduction/1024/1024,
				)
				m.lastRestoreDeferLogAt = time.Now()
			}
			return
		}
		targetSize = currentSize + units*unit
		if targetSize > m.innoDBBufferPreReduction {
			targetSize = m.innoDBBufferPreReduction
		}
	}

	actual, err := m.db.ResizeInnoDBBufferPool(targetSize)
	if err != nil {
		slog.Warn("failed to restore InnoDB buffer pool",
			"error", err,
			"target_mb", targetSize/1024/1024,
		)
		return
	}

	if actual >= m.innoDBBufferPreReduction {
		slog.Warn("restored InnoDB buffer pool",
			"to_mb", actual/1024/1024,
			"rss_at_reduction_mb", m.preReductionRSS/1024/1024,
		)
		m.innoDBBufferPreReduction = 0
		m.preReductionRSS = 0
	} else {
		slog.Warn("partially restored InnoDB buffer pool",
			"from_mb", currentSize/1024/1024,
			"to_mb", actual/1024/1024,
			"target_mb", m.innoDBBufferPreReduction/1024/1024,
			"remaining_mb", (m.innoDBBufferPreReduction-actual)/1024/1024,
		)
	}
}
