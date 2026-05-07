package main

import (
	"bufio"
	"context"
	"fmt"
	"log/slog"
	"net"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

type MemoryStatus struct {
	MemTotal     uint64
	MemAvailable uint64
	Cached       uint64
	SwapTotal    uint64
	SwapFree     uint64
	UsagePercent float64
	SwapPercent  float64
}

type cpuTimes struct {
	user, nice, system, idle, iowait, irq, softirq, steal uint64
}

func (c cpuTimes) total() uint64 {
	return c.user + c.nice + c.system + c.idle + c.iowait + c.irq + c.softirq + c.steal
}

type snapshotCache struct {
	prevCPU       *cpuTimes
	prevPgIn      uint64
	prevPgOut     uint64
	hasPgSnapshot bool
}

func checkPSI(resource string) (float64, error) {
	path := fmt.Sprintf("/proc/pressure/%s", resource)
	f, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return 0, nil
		}
		return 0, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()

	wantPrefix := "full "
	if resource == "cpu" {
		wantPrefix = "some "
	}

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, wantPrefix) {
			continue
		}
		fields := strings.Fields(line)
		for _, field := range fields {
			if strings.HasPrefix(field, "avg60=") {
				val, err := strconv.ParseFloat(strings.TrimPrefix(field, "avg60="), 64)
				if err != nil {
					return 0, fmt.Errorf("parse avg60 from %s: %w", path, err)
				}
				return val, nil
			}
		}
	}
	return 0, fmt.Errorf("no %q line found in %s", strings.TrimSpace(wantPrefix), path)
}

func readCPUTimes() (cpuTimes, error) {
	f, err := os.Open("/proc/stat")
	if err != nil {
		return cpuTimes{}, fmt.Errorf("open /proc/stat: %w", err)
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "cpu ") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 9 {
			return cpuTimes{}, fmt.Errorf("/proc/stat cpu line has %d fields, expected >=9", len(fields))
		}
		var ct cpuTimes
		vals := []*uint64{&ct.user, &ct.nice, &ct.system, &ct.idle, &ct.iowait, &ct.irq, &ct.softirq, &ct.steal}
		for i, ptr := range vals {
			v, err := strconv.ParseUint(fields[i+1], 10, 64)
			if err != nil {
				return cpuTimes{}, fmt.Errorf("parse /proc/stat field %d: %w", i+1, err)
			}
			*ptr = v
		}
		return ct, nil
	}
	return cpuTimes{}, fmt.Errorf("no 'cpu' line found in /proc/stat")
}

func checkIOWait(cache *snapshotCache) (float64, error) {
	current, err := readCPUTimes()
	if err != nil {
		return 0, err
	}

	if cache.prevCPU == nil {
		cache.prevCPU = &current
		return 0, nil
	}

	prev := cache.prevCPU
	cache.prevCPU = &current

	totalDelta := float64(current.total() - prev.total())
	if totalDelta == 0 {
		return 0, nil
	}

	iowaitDelta := float64(current.iowait - prev.iowait)
	return (iowaitDelta / totalDelta) * 100.0, nil
}

func readVmstatPages() (uint64, uint64, error) {
	f, err := os.Open("/proc/vmstat")
	if err != nil {
		return 0, 0, fmt.Errorf("open /proc/vmstat: %w", err)
	}
	defer f.Close()

	var pgpgin, pgpgout uint64
	found := 0
	scanner := bufio.NewScanner(f)
	for scanner.Scan() && found < 2 {
		fields := strings.Fields(scanner.Text())
		if len(fields) < 2 {
			continue
		}
		switch fields[0] {
		case "pgpgin":
			v, err := strconv.ParseUint(fields[1], 10, 64)
			if err != nil {
				return 0, 0, err
			}
			pgpgin = v
			found++
		case "pgpgout":
			v, err := strconv.ParseUint(fields[1], 10, 64)
			if err != nil {
				return 0, 0, err
			}
			pgpgout = v
			found++
		}
	}

	return pgpgin, pgpgout, nil
}

func checkPageRate(cache *snapshotCache, interval time.Duration) (float64, error) {
	in, out, err := readVmstatPages()
	if err != nil {
		return 0, err
	}

	if !cache.hasPgSnapshot {
		cache.prevPgIn = in
		cache.prevPgOut = out
		cache.hasPgSnapshot = true
		return 0, nil
	}

	prevIn := cache.prevPgIn
	prevOut := cache.prevPgOut
	cache.prevPgIn = in
	cache.prevPgOut = out

	totalDelta := float64((in + out) - (prevIn + prevOut))
	seconds := interval.Seconds()
	if seconds == 0 {
		return 0, nil
	}
	return totalDelta / seconds, nil
}

func checkMemory() (MemoryStatus, error) {
	f, err := os.Open("/proc/meminfo")
	if err != nil {
		return MemoryStatus{}, fmt.Errorf("open /proc/meminfo: %w", err)
	}
	defer f.Close()

	var ms MemoryStatus
	needed := map[string]*uint64{
		"MemTotal:":     &ms.MemTotal,
		"MemAvailable:": &ms.MemAvailable,
		"Cached:":       &ms.Cached,
		"SwapTotal:":    &ms.SwapTotal,
		"SwapFree:":     &ms.SwapFree,
	}

	found := 0
	scanner := bufio.NewScanner(f)
	for scanner.Scan() && found < len(needed) {
		fields := strings.Fields(scanner.Text())
		if len(fields) < 2 {
			continue
		}
		if ptr, ok := needed[fields[0]]; ok {
			v, err := strconv.ParseUint(fields[1], 10, 64)
			if err != nil {
				return MemoryStatus{}, fmt.Errorf("parse %s: %w", fields[0], err)
			}
			*ptr = v
			found++
		}
	}

	if ms.MemTotal > 0 {
		ms.UsagePercent = float64(ms.MemTotal-ms.MemAvailable) / float64(ms.MemTotal) * 100.0
	}
	if ms.SwapTotal > 0 {
		ms.SwapPercent = float64(ms.SwapTotal-ms.SwapFree) / float64(ms.SwapTotal) * 100.0
	}

	return ms, nil
}

func checkIOFreeze(timeout time.Duration) bool {
	done := make(chan bool, 1)

	go func() {
		f, err := os.CreateTemp("", "mariadb_monitor_io_test_*")
		if err != nil {
			done <- false
			return
		}
		path := f.Name()
		_, err = f.Write([]byte("io_test"))
		if err != nil {
			f.Close()
			os.Remove(path)
			done <- false
			return
		}
		_ = f.Sync()
		f.Close()
		os.Remove(path)
		done <- false
	}()

	select {
	case frozen := <-done:
		return frozen
	case <-time.After(timeout):
		return true
	}
}

func checkMachineFrozen() (bool, string) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	deadline, ok := ctx.Deadline()
	if !ok {
		deadline = time.Now().Add(2 * time.Second)
	}

	cmd := exec.CommandContext(ctx, "true")
	if err := cmd.Run(); err != nil {
		return true, "fork_failed"
	}

	r, w, err := os.Pipe()
	if err != nil {
		return true, "fd_exhausted"
	}
	r.Close()
	w.Close()

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return true, "tcp_listen_failed"
	}
	defer ln.Close()

	remaining := time.Until(deadline)
	if remaining <= 0 {
		return true, "deadline_exceeded"
	}

	errCh := make(chan error, 1)
	go func() {
		conn, err := ln.Accept()
		if err == nil {
			conn.Close()
		}
		errCh <- err
	}()

	dialTimeout := remaining
	if dialTimeout > time.Second {
		dialTimeout = time.Second
	}

	conn, err := net.DialTimeout("tcp", ln.Addr().String(), dialTimeout)
	if err != nil {
		return true, "tcp_dial_failed"
	}
	conn.Close()

	remaining = time.Until(deadline)
	if remaining <= 0 {
		return true, "deadline_exceeded"
	}
	acceptTimeout := remaining
	if acceptTimeout > time.Second {
		acceptTimeout = time.Second
	}

	select {
	case err := <-errCh:
		if err != nil {
			return true, "tcp_accept_failed"
		}
	case <-time.After(acceptTimeout):
		return true, "tcp_accept_timeout"
	}

	return false, ""
}

type metricWindows struct {
	psiCPU       MetricWindow
	psiMemory    MetricWindow
	psiIO        MetricWindow
	iowait       MetricWindow
	memUsage     MetricWindow
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
		pageRate:     NewMetricWindow(size),
		memAvailable: NewMetricWindow(size),
		memCached:    NewMetricWindow(size),
		swapFree:     NewMetricWindow(size),
	}
}

type frozenState struct {
	frozen bool
	reason string
}

// frozenProbeIntervalTicks is how often we run the (relatively expensive)
// machine-frozen probe when nothing else looks wrong. With a 5s check_interval
// this is once a minute. When any other trigger fires we run it immediately.
const frozenProbeIntervalTicks = 12

func (m *Monitor) collectTriggers() ([]string, *frozenState) {
	var triggers []string

	m.collectPSIMetrics()
	iowaitVal, iowaitErr := m.collectIOWait()
	mem, memErr := m.collectMemory()
	pageRateVal, _ := m.collectPageRate()

	triggers = append(triggers, m.evaluateThresholds(mem, memErr, iowaitVal, iowaitErr, pageRateVal)...)
	triggers = append(triggers, m.evaluatePredictiveTriggers(mem, memErr)...)

	// The frozen probe forks a process, opens an fd pair, and binds a TCP
	// socket. On a healthy node that work is wasted, so only run it when
	// something else already looks wrong, or once per minute as a sanity
	// check.
	var frozen *frozenState
	if len(triggers) > 0 || m.checkCount%frozenProbeIntervalTicks == 0 {
		frozen = m.checkMachineFrozen()
		if frozen != nil {
			triggers = append(triggers, fmt.Sprintf("machine_frozen(%s)", frozen.reason))
		}
	}

	m.updateCgroupPressureEvents()
	logSpikes(m.cfg, m.windows)

	return triggers, frozen
}

// collectPSIMetrics reads PSI cpu/memory/io and pushes them into windows.
func (m *Monitor) collectPSIMetrics() {
	for _, entry := range []struct {
		resource  string
		window    *MetricWindow
		threshold float64
	}{
		{"cpu", &m.windows.psiCPU, m.cfg.Thresholds.PSICPUThreshold},
		{"memory", &m.windows.psiMemory, m.cfg.Thresholds.PSIMemoryThreshold},
		{"io", &m.windows.psiIO, m.cfg.Thresholds.PSIIOThreshold},
	} {
		if val, err := checkPSI(entry.resource); err == nil {
			entry.window.Push(val, entry.threshold)
			slog.Debug(fmt.Sprintf("psi_%s", entry.resource), "avg60", val)
		} else {
			slog.Warn(fmt.Sprintf("failed to check psi %s", entry.resource), "error", err)
		}
	}
}

// collectIOWait computes iowait and pushes it into its window.
// Returns the value and any error so callers can reuse the result.
func (m *Monitor) collectIOWait() (float64, error) {
	val, err := checkIOWait(m.cache)
	if err == nil {
		m.windows.iowait.Push(val, m.cfg.Thresholds.IOWaitThreshold)
		slog.Debug("iowait", "percent", fmt.Sprintf("%.1f", val))
	} else {
		slog.Warn("failed to check iowait", "error", err)
	}
	return val, err
}

// collectMemory reads /proc/meminfo and pushes values into windows.
// Returns the reading and any error so callers can reuse the result.
func (m *Monitor) collectMemory() (MemoryStatus, error) {
	mem, err := checkMemory()
	if err == nil {
		m.windows.memUsage.Push(mem.UsagePercent, m.cfg.Thresholds.MemoryUsageThreshold)
		m.windows.memAvailable.Push(float64(mem.MemAvailable), 0)
		m.windows.memCached.Push(float64(mem.Cached), 0)
		m.windows.swapFree.Push(float64(mem.SwapFree), 0)
		slog.Debug("memory",
			"usage_percent", fmt.Sprintf("%.1f", mem.UsagePercent),
			"mem_available_kb", mem.MemAvailable,
			"cached_kb", mem.Cached,
			"swap_free_kb", mem.SwapFree,
		)
	} else {
		slog.Warn("failed to check memory", "error", err)
	}
	return mem, err
}

// collectPageRate reads vmstat page rates and pushes into its window.
func (m *Monitor) collectPageRate() (float64, error) {
	val, err := checkPageRate(m.cache, m.cfg.CheckInterval)
	if err == nil {
		m.windows.pageRate.Push(val, m.cfg.Thresholds.PageRateThreshold)
		slog.Debug("page_rate", "pages_per_sec", val)
	} else {
		slog.Warn("failed to check page rate", "error", err)
	}
	return val, err
}

// evaluateThresholds checks all sustained and instantaneous thresholds.
func (m *Monitor) evaluateThresholds(mem MemoryStatus, memErr error, iowaitVal float64, iowaitErr error, pageRateVal float64) []string {
	var triggers []string

	if memErr == nil && mem.UsagePercent >= m.cfg.Thresholds.CriticalMemoryThreshold {
		triggers = append(triggers, fmt.Sprintf("critical_memory=%.1f%%", mem.UsagePercent))
	}

	if iowaitErr == nil && iowaitVal >= m.cfg.Thresholds.IOWaitThreshold {
		if checkIOFreeze(m.cfg.Thresholds.IOFreezeTimeout) {
			triggers = append(triggers, "io_freeze")
		}
	}

	if m.windows.psiCPU.IsSustained(m.cfg.Monitor.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_cpu")
	}
	if m.windows.psiMemory.IsSustained(m.cfg.Monitor.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_memory")
	}
	if m.windows.psiIO.IsSustained(m.cfg.Monitor.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_io")
	}
	if m.windows.iowait.IsSustained(m.cfg.Monitor.SustainedRatio) {
		triggers = append(triggers, "sustained_iowait")
	}
	if m.windows.memUsage.IsSustained(m.cfg.Monitor.SustainedRatio) {
		triggers = append(triggers, "sustained_memory_usage")
	}

	cgSwap := readCgroupMemory()
	swapThresholdBytes := m.cfg.Thresholds.MariaDBSwapThresholdMB * 1024 * 1024
	if swapThresholdBytes > 0 && cgSwap.SwapUsage >= swapThresholdBytes {
		triggers = append(triggers, fmt.Sprintf("mariadb_swap_usage=%dMB", cgSwap.SwapUsage/1024/1024))
		slog.Debug("mariadb cgroup swap", "swap_mb", cgSwap.SwapUsage/1024/1024, "threshold_mb", m.cfg.Thresholds.MariaDBSwapThresholdMB)
	}

	if m.windows.pageRate.IsSustained(m.cfg.Monitor.SustainedRatio) {
		triggers = append(triggers, "sustained_page_rate")
	}

	return triggers
}

// evaluatePredictiveTriggers adds triggers based on trend analysis.
func (m *Monitor) evaluatePredictiveTriggers(mem MemoryStatus, memErr error) []string {
	var triggers []string
	if memErr != nil || mem.SwapTotal == 0 {
		return triggers
	}

	swapFreePercent := float64(mem.SwapFree) / float64(mem.SwapTotal) * 100.0
	if m.windows.memAvailable.Trend() == "falling" &&
		m.windows.memCached.Trend() == "falling" &&
		swapFreePercent < m.cfg.Thresholds.SwapHeadroom {
		triggers = append(triggers, fmt.Sprintf("predictive_memory_exhaustion(swap_free=%.1f%%)", swapFreePercent))
	}
	return triggers
}

// checkMachineFrozen runs the machine-frozen probe if needed.
func (m *Monitor) checkMachineFrozen() *frozenState {
	if isFrozen, reason := checkMachineFrozen(); isFrozen {
		return &frozenState{frozen: true, reason: reason}
	}
	return nil
}

// updateCgroupPressureEvents tracks cgroup memory.high / memory.max deltas.
func (m *Monitor) updateCgroupPressureEvents() {
	cgMem := readCgroupMemory()
	if cgMem.HighEvents > m.lastCgroupHighEvents || cgMem.MaxEvents > m.lastCgroupMaxEvents {
		m.memHighHitsConsecutive++
		slog.Debug("cgroup memory pressure events",
			"new_high_events", cgMem.HighEvents-m.lastCgroupHighEvents,
			"new_max_events", cgMem.MaxEvents-m.lastCgroupMaxEvents,
			"consecutive_ticks", m.memHighHitsConsecutive,
		)
	} else {
		m.memHighHitsConsecutive = 0
	}
	m.lastCgroupHighEvents = cgMem.HighEvents
	m.lastCgroupMaxEvents = cgMem.MaxEvents
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
		{"page_rate", &w.pageRate},
	}
	for _, s := range spikes {
		if s.window.IsSpike(cfg.Monitor.SustainedRatio) {
			latest := s.window.buf.Latest()
			slog.Info("spike detected",
				"metric", s.name,
				"value", fmt.Sprintf("%.1f", latest.value),
				"trend", s.window.Trend(),
			)
		}
	}
}
