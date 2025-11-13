package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// ProcessInfo represents a process with its resource usage
type ProcessInfo struct {
	Name  string
	Usage uint64 // bytes for memory, bytes for disk I/O
}

// StatsSample represents a single snapshot of system statistics
type StatsSample struct {
	Timestamp time.Time

	CPU struct {
		UserPercent   float64
		SystemPercent float64
		IOwaitPercent float64
		IdlePercent   float64
	}

	Memory struct {
		TotalBytes          uint64
		CacheBytes          uint64
		ActualUsedBytes     uint64
		ReclaimableBytes    uint64
		NonReclaimableBytes uint64
	}

	Swap struct {
		UsedBytes        uint64
		PageInPerSecond  float64
		PageOutPerSecond float64
	}

	Disk struct {
		ReadIOPS             float64
		WriteIOPS            float64
		ReadThroughputBytes  float64
		WriteThroughputBytes float64
		ReadLatencyMillis    float64
		WriteLatencyMillis   float64
		QueueDepth           float64
	}

	PSI struct {
		IO_SomeAvg10     float64
		IO_FullAvg10     float64
		Memory_SomeAvg10 float64
		Memory_FullAvg10 float64
		CPU_SomeAvg10    float64
		CPU_FullAvg10    float64
	}

	TopMemoryProcesses []ProcessInfo // Top 5 memory consuming processes
	TopCPUProcesses    []ProcessInfo // Top 5 CPU consuming processes (Usage = percentage * 100)
}

// diskAgg aggregates disk statistics across all devices
type diskAgg struct {
	readIOs, readSectors, readTicks    uint64
	writeIOs, writeSectors, writeTicks uint64
	ioTicks                            uint64
}

// Sampler collects and stores system statistics samples
type Sampler struct {
	buf *CircularBuffer[StatsSample]

	lastCPU struct {
		user, system, iowait, idle, total uint64
		valid                             bool
	}
	lastDisk struct {
		diskAgg
		valid bool
	}
	lastSwapIn  uint64
	lastSwapOut uint64
	lastSwapSet bool
}

// Start begins periodic collection of system statistics
func (m *Monitor) StartStatsSampler() {
	tick := time.NewTicker(SampleInterval)
	m.wg.Add(1)
	defer m.wg.Done()
	defer tick.Stop()
	for {
		select {
		case <-m.ctx.Done():
			fmt.Println("Sampler stopping:", m.ctx.Err())
			return
		case <-tick.C:
			m.sampler.collect()
		}
	}
}

func (s *Sampler) collect() {
	now := time.Now()

	// CPU
	u, sys, io, idle, tot, _ := parseCPU()
	var userPct, sysPct, ioPct, idlePct float64
	if s.lastCPU.valid && tot > s.lastCPU.total {
		td := float64(tot - s.lastCPU.total)
		userPct = 100 * float64(u-s.lastCPU.user) / td
		sysPct = 100 * float64(sys-s.lastCPU.system) / td
		ioPct = 100 * float64(io-s.lastCPU.iowait) / td
		idlePct = 100 * float64(idle-s.lastCPU.idle) / td
	}
	s.lastCPU.user = u
	s.lastCPU.system = sys
	s.lastCPU.iowait = io
	s.lastCPU.idle = idle
	s.lastCPU.total = tot
	s.lastCPU.valid = true

	// Memory
	mem, _ := parseMemInfo()
	total := mem["MemTotal"]
	cache := mem["Cached"] + mem["Buffers"]
	reclaimable := mem["SReclaimable"]
	slab := mem["Slab"]
	nonReclaimable := uint64(0)
	if slab > reclaimable {
		nonReclaimable = slab - reclaimable
	}
	actualUsed := total - mem["MemFree"] - cache - reclaimable

	// Swap
	swpIn, swpOut, _ := parseVMStat()
	swapUsed := mem["SwapTotal"] - mem["SwapFree"]
	var swapInPS, swapOutPS float64
	if s.lastSwapSet {
		swapInPS = float64(swpIn-s.lastSwapIn) / SampleInterval.Seconds()
		swapOutPS = float64(swpOut-s.lastSwapOut) / SampleInterval.Seconds()
	}
	s.lastSwapIn = swpIn
	s.lastSwapOut = swpOut
	s.lastSwapSet = true

	// Disk
	disk, _ := parseDiskstats()
	var readIOPS, writeIOPS, readBps, writeBps, readLat, writeLat, qdepth float64
	if s.lastDisk.valid {
		dt := SampleInterval.Seconds()
		readDelta := disk.readIOs - s.lastDisk.readIOs
		writeDelta := disk.writeIOs - s.lastDisk.writeIOs
		readIOPS = float64(readDelta) / dt
		writeIOPS = float64(writeDelta) / dt
		readBps = float64(disk.readSectors-s.lastDisk.readSectors) * SectorSize / dt
		writeBps = float64(disk.writeSectors-s.lastDisk.writeSectors) * SectorSize / dt
		if readDelta > 0 {
			readLat = float64(disk.readTicks-s.lastDisk.readTicks) / float64(readDelta)
		}
		if writeDelta > 0 {
			writeLat = float64(disk.writeTicks-s.lastDisk.writeTicks) / float64(writeDelta)
		}
		ioTicks := disk.ioTicks - s.lastDisk.ioTicks
		if ioTicks > 0 {
			qdepth = (float64(ioTicks) / 1000.0) * (readIOPS + writeIOPS)
		}
	}
	s.lastDisk.diskAgg = disk
	s.lastDisk.valid = true

	// PSI
	ioSome, ioFull, _ := parsePSI("io")
	memSome, memFull, _ := parsePSI("memory")
	cpuSome, cpuFull, _ := parsePSI("cpu")

	// Build sample
	sample := StatsSample{Timestamp: now}

	sample.CPU.UserPercent = userPct
	sample.CPU.SystemPercent = sysPct
	sample.CPU.IOwaitPercent = ioPct
	sample.CPU.IdlePercent = idlePct

	sample.Memory.TotalBytes = total
	sample.Memory.CacheBytes = cache
	sample.Memory.ActualUsedBytes = actualUsed
	sample.Memory.ReclaimableBytes = reclaimable
	sample.Memory.NonReclaimableBytes = nonReclaimable

	sample.Swap.UsedBytes = swapUsed
	sample.Swap.PageInPerSecond = swapInPS
	sample.Swap.PageOutPerSecond = swapOutPS

	sample.Disk.ReadIOPS = readIOPS
	sample.Disk.WriteIOPS = writeIOPS
	sample.Disk.ReadThroughputBytes = readBps
	sample.Disk.WriteThroughputBytes = writeBps
	sample.Disk.ReadLatencyMillis = readLat
	sample.Disk.WriteLatencyMillis = writeLat
	sample.Disk.QueueDepth = qdepth

	sample.PSI.IO_SomeAvg10 = ioSome
	sample.PSI.IO_FullAvg10 = ioFull
	sample.PSI.Memory_SomeAvg10 = memSome
	sample.PSI.Memory_FullAvg10 = memFull
	sample.PSI.CPU_SomeAvg10 = cpuSome
	sample.PSI.CPU_FullAvg10 = cpuFull

	// Top Processes
	sample.TopMemoryProcesses = getTopMemoryProcesses()
	sample.TopCPUProcesses = getTopCPUProcesses()

	s.buf.Add(sample)
}

// parseCPU reads CPU statistics from /proc/stat
func parseCPU() (user, system, iowait, idle, total uint64, err error) {
	f, err := os.Open("/proc/stat")
	if err != nil {
		return
	}
	defer f.Close()

	sc := bufio.NewScanner(f)
	if sc.Scan() {
		fields := strings.Fields(sc.Text())
		if len(fields) < 6 || fields[0] != "cpu" {
			err = fmt.Errorf("unexpected /proc/stat format")
			return
		}
		parse := func(i int) uint64 {
			if i >= len(fields) {
				return 0
			}
			v, _ := strconv.ParseUint(fields[i], 10, 64)
			return v
		}
		user = parse(1)
		system = parse(3)
		idle = parse(4)
		iowait = parse(5)
		for i := 1; i < len(fields); i++ {
			v, _ := strconv.ParseUint(fields[i], 10, 64)
			total += v
		}
	}
	return
}

// parseMemInfo reads memory statistics from /proc/meminfo
func parseMemInfo() (map[string]uint64, error) {
	f, err := os.Open("/proc/meminfo")
	if err != nil {
		return nil, err
	}
	defer f.Close()

	m := make(map[string]uint64)
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		parts := strings.Fields(sc.Text())
		if len(parts) < 2 {
			continue
		}
		key := strings.TrimSuffix(parts[0], ":")
		val, _ := strconv.ParseUint(parts[1], 10, 64)
		m[key] = val * 1024 // convert kB → bytes
	}
	return m, sc.Err()
}

// parseVMStat reads swap statistics from /proc/vmstat
func parseVMStat() (pageIn, pageOut uint64, err error) {
	f, err := os.Open("/proc/vmstat")
	if err != nil {
		return
	}
	defer f.Close()

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		parts := strings.Fields(sc.Text())
		if len(parts) != 2 {
			continue
		}
		switch parts[0] {
		case "pswpin":
			pageIn, _ = strconv.ParseUint(parts[1], 10, 64)
		case "pswpout":
			pageOut, _ = strconv.ParseUint(parts[1], 10, 64)
		}
	}
	return
}

// parseDiskstats reads disk I/O statistics from /proc/diskstats
func parseDiskstats() (diskAgg, error) {
	var agg diskAgg
	f, err := os.Open("/proc/diskstats")
	if err != nil {
		return agg, err
	}
	defer f.Close()

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		fields := strings.Fields(sc.Text())
		if len(fields) < 14 {
			continue
		}
		name := fields[2]
		// Skip loop and ram devices
		if strings.HasPrefix(name, "loop") || strings.HasPrefix(name, "ram") {
			continue
		}

		readIOs, _ := strconv.ParseUint(fields[3], 10, 64)
		readSectors, _ := strconv.ParseUint(fields[5], 10, 64)
		readTicks, _ := strconv.ParseUint(fields[6], 10, 64)
		writeIOs, _ := strconv.ParseUint(fields[7], 10, 64)
		writeSectors, _ := strconv.ParseUint(fields[9], 10, 64)
		writeTicks, _ := strconv.ParseUint(fields[10], 10, 64)
		ioTicks, _ := strconv.ParseUint(fields[12], 10, 64)

		agg.readIOs += readIOs
		agg.readSectors += readSectors
		agg.readTicks += readTicks
		agg.writeIOs += writeIOs
		agg.writeSectors += writeSectors
		agg.writeTicks += writeTicks
		agg.ioTicks += ioTicks
	}
	return agg, sc.Err()
}

// parsePSI reads pressure stall information for a given resource
func parsePSI(resource string) (someAvg10, fullAvg10 float64, err error) {
	path := filepath.Join("/proc/pressure", resource)
	f, err := os.Open(path)
	if err != nil {
		return 0, 0, fmt.Errorf("missing PSI: %s", resource)
	}
	defer f.Close()

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := sc.Text()
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		switch fields[0] {
		case "some":
			for _, f := range fields[1:] {
				if strings.HasPrefix(f, "avg10=") {
					someAvg10, _ = strconv.ParseFloat(strings.TrimPrefix(f, "avg10="), 64)
				}
			}
		case "full":
			for _, f := range fields[1:] {
				if strings.HasPrefix(f, "avg10=") {
					fullAvg10, _ = strconv.ParseFloat(strings.TrimPrefix(f, "avg10="), 64)
				}
			}
		}
	}
	return
}

// getTopMemoryProcesses returns the top 5 memory consuming processes
func getTopMemoryProcesses() []ProcessInfo {
	procDir, err := os.Open("/proc")
	if err != nil {
		return nil
	}
	defer procDir.Close()

	entries, err := procDir.Readdirnames(-1)
	if err != nil {
		return nil
	}

	var processes []ProcessInfo
	for _, entry := range entries {
		// Check if entry is a PID (numeric)
		if _, err := strconv.Atoi(entry); err != nil {
			continue
		}

		// Read process name
		commPath := filepath.Join("/proc", entry, "comm")
		commData, err := os.ReadFile(commPath)
		if err != nil {
			continue
		}
		name := strings.TrimSpace(string(commData))

		// Read memory usage from status
		statusPath := filepath.Join("/proc", entry, "status")
		statusFile, err := os.Open(statusPath)
		if err != nil {
			continue
		}

		var rssKB uint64
		scanner := bufio.NewScanner(statusFile)
		for scanner.Scan() {
			line := scanner.Text()
			if strings.HasPrefix(line, "VmRSS:") {
				fields := strings.Fields(line)
				if len(fields) >= 2 {
					rssKB, _ = strconv.ParseUint(fields[1], 10, 64)
					break
				}
			}
		}
		statusFile.Close()

		if rssKB > 0 {
			processes = append(processes, ProcessInfo{
				Name:  name,
				Usage: rssKB * 1024, // Convert kB to bytes
			})
		}
	}

	// Sort by usage (descending)
	sort.Slice(processes, func(i, j int) bool {
		return processes[i].Usage > processes[j].Usage
	})

	// Return top 5
	if len(processes) > 5 {
		processes = processes[:5]
	}
	return processes
}

// getTopCPUProcesses returns the top 5 CPU consuming processes
func getTopCPUProcesses() []ProcessInfo {
	procDir, err := os.Open("/proc")
	if err != nil {
		return nil
	}
	defer procDir.Close()

	entries, err := procDir.Readdirnames(-1)
	if err != nil {
		return nil
	}

	// Get system uptime for CPU calculation
	uptimeData, err := os.ReadFile("/proc/uptime")
	if err != nil {
		return nil
	}
	uptimeFields := strings.Fields(string(uptimeData))
	if len(uptimeFields) < 1 {
		return nil
	}
	uptime, _ := strconv.ParseFloat(uptimeFields[0], 64)

	var processes []ProcessInfo
	for _, entry := range entries {
		// Check if entry is a PID (numeric)
		if _, err := strconv.Atoi(entry); err != nil {
			continue
		}

		// Read process name
		commPath := filepath.Join("/proc", entry, "comm")
		commData, err := os.ReadFile(commPath)
		if err != nil {
			continue
		}
		name := strings.TrimSpace(string(commData))

		// Read CPU times from /proc/[pid]/stat
		statPath := filepath.Join("/proc", entry, "stat")
		statData, err := os.ReadFile(statPath)
		if err != nil {
			continue
		}

		// Parse stat file
		statStr := string(statData)
		// Find the last ')' to handle process names with spaces/parentheses
		lastParen := strings.LastIndex(statStr, ")")
		if lastParen == -1 {
			continue
		}
		fields := strings.Fields(statStr[lastParen+1:])
		if len(fields) < 20 {
			continue
		}

		// Fields after process name: state utime stime cutime cstime...
		// utime is at index 11, stime at 12, starttime at 19 (in original stat)
		// After removing name part, utime is at index 11, stime at 12, starttime at 19
		utime, _ := strconv.ParseUint(fields[11], 10, 64)
		stime, _ := strconv.ParseUint(fields[12], 10, 64)
		starttime, _ := strconv.ParseUint(fields[19], 10, 64)

		// Calculate CPU percentage
		// Total CPU time in clock ticks
		totalTime := float64(utime + stime)
		// Process uptime in seconds
		clockTicks := 100.0 // sysconf(_SC_CLK_TCK) is typically 100
		processUptime := uptime - (float64(starttime) / clockTicks)
		if processUptime <= 0 {
			continue
		}

		// CPU percentage = (total_time / clock_ticks / process_uptime) * 100 * num_cpu
		cpuPercent := (totalTime / clockTicks / processUptime) * 100.0

		// Store as integer (percentage * 100 to preserve precision)
		cpuUsage := uint64(cpuPercent * 100)

		if cpuUsage > 0 {
			processes = append(processes, ProcessInfo{
				Name:  name,
				Usage: cpuUsage,
			})
		}
	}

	// Sort by usage (descending)
	sort.Slice(processes, func(i, j int) bool {
		return processes[i].Usage > processes[j].Usage
	})

	// Return top 5
	if len(processes) > 5 {
		processes = processes[:5]
	}
	return processes
}
