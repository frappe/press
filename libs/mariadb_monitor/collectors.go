package main

import (
	"bufio"
	"context"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
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

type cpuTimes struct {
	user, nice, system, idle, iowait, irq, softirq, steal uint64
}

func (c cpuTimes) total() uint64 {
	return c.user + c.nice + c.system + c.idle + c.iowait + c.irq + c.softirq + c.steal
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

type snapshotCache struct {
	prevCPU       *cpuTimes
	prevPgIn      uint64
	prevPgOut     uint64
	hasPgSnapshot bool
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
		path := filepath.Join(os.TempDir(), ".mariadb_monitor_io_test")
		f, err := os.Create(path)
		if err != nil {
			done <- false
			return
		}
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
		done <- false // I/O completed, not frozen
	}()

	select {
	case frozen := <-done:
		return frozen
	case <-time.After(timeout):
		return true // timed out, I/O is frozen
	}
}

func checkMachineFrozen() (bool, string) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	deadline, ok := ctx.Deadline()
	if !ok {
		// Fallback: context should always have a deadline here, but be defensive.
		deadline = time.Now().Add(2 * time.Second)
	}

	// 1. Check process spawning (fork/exec). Tests PID limits, memory for fork, and basic scheduling.
	cmd := exec.CommandContext(ctx, "true")
	if err := cmd.Run(); err != nil {
		return true, "fork_failed"
	}

	// 2. Check File Descriptor (FD) limits. SSH often hangs when the OS runs out of file handles.
	r, w, err := os.Pipe()
	if err != nil {
		return true, "fd_exhausted"
	}
	r.Close()
	w.Close()

	// 3. Check Network Stack and Memory limits. 
	// Verifies if the OS has enough memory to open, dial, and accept TCP connections.
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return true, "tcp_listen_failed"
	}
	defer ln.Close()

	// Ensure we still have time left in the overall budget before network checks.
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

	// Dial timeout is derived from the remaining overall budget, capped at 1s.
	dialTimeout := remaining
	if dialTimeout > time.Second {
		dialTimeout = time.Second
	}

	conn, err := net.DialTimeout("tcp", ln.Addr().String(), dialTimeout)
	if err != nil {
		return true, "tcp_dial_failed"
	}
	conn.Close()

	// Recompute remaining time for the accept phase, again capped at 1s.
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
