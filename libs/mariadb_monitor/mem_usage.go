package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const cgroupPath = "/sys/fs/cgroup/system.slice/mariadb.service"

// MemoryUsage holds MariaDB memory estimates and system-level cgroup readings.
type MemoryUsage struct {
	// Engine contains memory estimates reported by MariaDB internals.
	Engine EngineMemory

	// Cgroup contains memory controller readings from the systemd service cgroup.
	Cgroup CgroupMemory
}

// EngineMemory holds an estimated breakdown of MariaDB memory by subsystem.
// All values are in bytes.
type EngineMemory struct {
	InnoDBBufferPoolUsed uint64
	InnoDBLogBuffer      uint64
	KeyBufferUsed        uint64
	ThreadStacks         uint64
	SortBuffers          uint64
	JoinBuffers          uint64
	ReadBuffers          uint64
	QueryCacheUsed       uint64
	PSTableMemory        uint64 // (pfs_table).memory from SHOW ENGINE PERFORMANCE_SCHEMA STATUS
	PSOtherMemory        uint64 // sum of all other .memory entries from PS status
	TotalTracked         uint64
}

// CgroupMemory holds cgroup v2 memory controller readings.
// Byte values are in bytes; event values are counts.
type CgroupMemory struct {
	CurrentUsage uint64 // memory.current
	MemoryHigh   uint64 // memory.high throttle limit
	MemoryMax    uint64 // memory.max hard limit
	SwapUsage    uint64 // memory.swap.current
	HighEvents   uint64 // memory.events: times memory.high was exceeded
	MaxEvents    uint64 // memory.events: times memory.max was approached
	OOMEvents    uint64 // memory.events: times OOM occurred
	OOMKills     uint64 // memory.events: processes killed by OOM killer
}

// GetMemoryUsage returns an estimated breakdown of MariaDB memory usage.
// It queries SHOW GLOBAL STATUS, SHOW GLOBAL VARIABLES, and
// SHOW ENGINE PERFORMANCE_SCHEMA STATUS (skipped if PS is disabled),
// and reads cgroup v2 memory information.
func GetMemoryUsage(d *Database) (MemoryUsage, error) {
	status, err := d.queryKVUint64("SHOW GLOBAL STATUS")
	if err != nil {
		return MemoryUsage{}, fmt.Errorf("SHOW GLOBAL STATUS: %w", err)
	}
	vars, err := d.queryKVUint64("SHOW GLOBAL VARIABLES")
	if err != nil {
		return MemoryUsage{}, fmt.Errorf("SHOW GLOBAL VARIABLES: %w", err)
	}

	var mu MemoryUsage

	// InnoDB buffer pool
	pageSize := vars["innodb_page_size"]
	if pageSize == 0 {
		pageSize = 16384
	}
	mu.Engine.InnoDBBufferPoolUsed = (status["innodb_buffer_pool_pages_data"] +
		status["innodb_buffer_pool_pages_dirty"]) * pageSize
	mu.Engine.InnoDBLogBuffer = vars["innodb_log_buffer_size"]

	// MyISAM key cache
	blockSize := vars["key_cache_block_size"]
	if blockSize == 0 {
		blockSize = 1024
	}
	mu.Engine.KeyBufferUsed = status["key_blocks_used"] * blockSize

	// Per-connection session buffers
	threads := status["threads_connected"]
	if threads == 0 {
		threads = 1
	}
	mu.Engine.ThreadStacks = vars["thread_stack"] * threads
	mu.Engine.SortBuffers = vars["sort_buffer_size"] * threads
	mu.Engine.JoinBuffers = vars["join_buffer_size"] * threads
	mu.Engine.ReadBuffers = (vars["read_buffer_size"] + vars["read_rnd_buffer_size"]) * threads

	// Query cache
	if qcs := vars["query_cache_size"]; qcs > 0 {
		mu.Engine.QueryCacheUsed = qcs - status["qcache_free_memory"]
	}

	// Performance schema memory - skipped silently if PS is disabled.
	_ = d.Query("SHOW ENGINE PERFORMANCE_SCHEMA STATUS", func(rows *sql.Rows) error {
		for rows.Next() {
			var typ, name, val string
			if err := rows.Scan(&typ, &name, &val); err != nil {
				return err
			}
			if !strings.HasSuffix(name, ".memory") {
				continue
			}
			n, err := strconv.ParseUint(val, 10, 64)
			if err != nil {
				continue
			}
			if name == "(pfs_table).memory" {
				mu.Engine.PSTableMemory = n
			} else {
				mu.Engine.PSOtherMemory += n
			}
		}
		return nil
	})

	mu.Engine.TotalTracked = mu.Engine.InnoDBLogBuffer +
		mu.Engine.KeyBufferUsed +
		mu.Engine.ThreadStacks +
		mu.Engine.SortBuffers +
		mu.Engine.JoinBuffers +
		mu.Engine.ReadBuffers +
		mu.Engine.QueryCacheUsed +
		mu.Engine.PSTableMemory +
		mu.Engine.PSOtherMemory

	mu.Cgroup = readCgroupMemory()

	return mu, nil
}

func readCgroupMemory() CgroupMemory {
	var sm CgroupMemory

	sm.CurrentUsage = readUint64File(filepath.Join(cgroupPath, "memory.current"))
	sm.MemoryHigh = parseCgroupV2Max(filepath.Join(cgroupPath, "memory.high"))
	sm.MemoryMax = parseCgroupV2Max(filepath.Join(cgroupPath, "memory.max"))
	sm.SwapUsage = readUint64File(filepath.Join(cgroupPath, "memory.swap.current"))
	sm.HighEvents, sm.MaxEvents, sm.OOMEvents, sm.OOMKills = readCgroupEvents(filepath.Join(cgroupPath, "memory.events"))

	return sm
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
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	for _, line := range lines {
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
