package main

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const cgroupPath = "/sys/fs/cgroup/system.slice/mariadb.service"

// CgroupMemory holds the cgroup v2 memory controller readings for mariadb.service.
type CgroupMemory struct {
	CurrentUsage uint64 // memory.current
	MemoryHigh   uint64 // memory.high (soft throttle; "max" -> 0)
	MemoryMax    uint64 // memory.max  (hard OOM limit; "max" -> 0)
	SwapUsage    uint64 // memory.swap.current
	HighEvents   uint64 // memory.events: times memory.high was hit
	MaxEvents    uint64 // memory.events: times memory.max was approached
	OOMEvents    uint64 // memory.events: oom
	OOMKills     uint64 // memory.events: oom_kill
}

func readCgroupMemory() CgroupMemory {
	var c CgroupMemory
	c.CurrentUsage = readUint64File(filepath.Join(cgroupPath, "memory.current"))
	c.MemoryHigh = parseCgroupV2Max(filepath.Join(cgroupPath, "memory.high"))
	c.MemoryMax = parseCgroupV2Max(filepath.Join(cgroupPath, "memory.max"))
	c.SwapUsage = readUint64File(filepath.Join(cgroupPath, "memory.swap.current"))
	c.HighEvents, c.MaxEvents, c.OOMEvents, c.OOMKills =
		readCgroupEvents(filepath.Join(cgroupPath, "memory.events"))
	return c
}

func readUint64File(path string) uint64 {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0
	}
	n, err := strconv.ParseUint(strings.TrimSpace(string(data)), 10, 64)
	if err != nil {
		return 0
	}
	return n
}

// parseCgroupV2Max parses a cgroup v2 limit file where "max" means unlimited.
func parseCgroupV2Max(path string) uint64 {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0
	}
	s := strings.TrimSpace(string(data))
	if s == "max" {
		return 0
	}
	n, err := strconv.ParseUint(s, 10, 64)
	if err != nil {
		return 0
	}
	return n
}

func readCgroupEvents(path string) (high, max, oom, oomKill uint64) {
	data, err := os.ReadFile(path)
	if err != nil {
		return
	}
	for _, line := range strings.Split(strings.TrimSpace(string(data)), "\n") {
		fields := strings.Fields(line)
		if len(fields) != 2 {
			continue
		}
		n, err := strconv.ParseUint(fields[1], 10, 64)
		if err != nil {
			continue
		}
		switch fields[0] {
		case "high":
			high = n
		case "max":
			max = n
		case "oom":
			oom = n
		case "oom_kill":
			oomKill = n
		}
	}
	return
}
