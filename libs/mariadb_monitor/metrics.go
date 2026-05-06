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

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "some ") {
			continue
		}
		fields := strings.Fields(line)
		for _, field := range fields {
			if strings.HasPrefix(field, "avg10=") {
				val, err := strconv.ParseFloat(strings.TrimPrefix(field, "avg10="), 64)
				if err != nil {
					return 0, fmt.Errorf("parse avg10 from %s: %w", path, err)
				}
				return val, nil
			}
		}
	}
	return 0, fmt.Errorf("no 'some' line found in %s", path)
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

type frozenState struct {
	frozen bool
	reason string
}

func (m *Monitor) collectTriggers() ([]string, *frozenState) {
	var triggers []string
	var frozen *frozenState

	if val, err := checkPSI("cpu"); err == nil {
		m.windows.psiCPU.Push(val, m.cfg.PSICPUThreshold)
		slog.Debug("psi_cpu", "avg10", val)
	} else {
		slog.Warn("failed to check psi cpu", "error", err)
	}

	if val, err := checkPSI("memory"); err == nil {
		m.windows.psiMemory.Push(val, m.cfg.PSIMemoryThreshold)
		slog.Debug("psi_memory", "avg10", val)
	} else {
		slog.Warn("failed to check psi memory", "error", err)
	}

	if val, err := checkPSI("io"); err == nil {
		m.windows.psiIO.Push(val, m.cfg.PSIIOThreshold)
		slog.Debug("psi_io", "avg10", val)
	} else {
		slog.Warn("failed to check psi io", "error", err)
	}

	iowaitVal, iowaitErr := checkIOWait(m.cache)
	if iowaitErr == nil {
		m.windows.iowait.Push(iowaitVal, m.cfg.IOWaitThreshold)
		slog.Debug("iowait", "percent", fmt.Sprintf("%.1f", iowaitVal))
	} else {
		slog.Warn("failed to check iowait", "error", iowaitErr)
	}

	mem, memErr := checkMemory()
	if memErr == nil {
		m.windows.memUsage.Push(mem.UsagePercent, m.cfg.MemoryUsageThreshold)
		m.windows.swapUsage.Push(mem.SwapPercent, m.cfg.SwapUsageThreshold)
		m.windows.memAvailable.Push(float64(mem.MemAvailable), 0)
		m.windows.memCached.Push(float64(mem.Cached), 0)
		m.windows.swapFree.Push(float64(mem.SwapFree), 0)

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

	pageRateVal, pageRateErr := checkPageRate(m.cache, m.cfg.CheckInterval)
	if pageRateErr == nil {
		m.windows.pageRate.Push(pageRateVal, m.cfg.PageRateThreshold)
		slog.Debug("page_rate", "pages_per_sec", pageRateVal)
	} else {
		slog.Warn("failed to check page rate", "error", pageRateErr)
	}

	if memErr == nil && mem.UsagePercent >= m.cfg.CriticalMemoryThreshold {
		triggers = append(triggers, fmt.Sprintf("critical_memory=%.1f%%", mem.UsagePercent))
	}

	if iowaitErr == nil && iowaitVal >= m.cfg.IOWaitThreshold {
		if checkIOFreeze(m.cfg.IOFreezeTimeout) {
			triggers = append(triggers, "io_freeze")
		}
	}

	if m.windows.psiCPU.IsSustained(m.cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_cpu")
	}
	if m.windows.psiMemory.IsSustained(m.cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_memory")
	}
	if m.windows.psiIO.IsSustained(m.cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_psi_io")
	}
	if m.windows.iowait.IsSustained(m.cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_iowait")
	}
	if m.windows.memUsage.IsSustained(m.cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_memory_usage")
	}
	if m.windows.swapUsage.IsSustained(m.cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_swap_usage")
	}
	if m.windows.pageRate.IsSustained(m.cfg.SustainedRatio) {
		triggers = append(triggers, "sustained_page_rate")
	}

	if isFrozen, reason := checkMachineFrozen(); isFrozen {
		frozen = &frozenState{frozen: true, reason: reason}
		triggers = append(triggers, fmt.Sprintf("machine_frozen(%s)", reason))
	}

	if memErr == nil && mem.SwapTotal > 0 {
		swapFreePercent := float64(mem.SwapFree) / float64(mem.SwapTotal) * 100.0
		if m.windows.memAvailable.Trend() == "falling" &&
			m.windows.memCached.Trend() == "falling" &&
			swapFreePercent < m.cfg.SwapHeadroom {
			triggers = append(triggers, fmt.Sprintf("predictive_memory_exhaustion(swap_free=%.1f%%)", swapFreePercent))
		}
	}

	logSpikes(m.cfg, m.windows)
	return triggers, frozen
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
			slog.Info("spike detected",
				"metric", s.name,
				"value", fmt.Sprintf("%.1f", latest.value),
				"trend", s.window.Trend(),
			)
		}
	}
}
