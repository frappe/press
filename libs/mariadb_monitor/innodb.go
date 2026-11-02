package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// ReadConfiguredBufferPoolSize scans *.cnf files under /etc/mysql/conf.d and
// /etc/mysql/mariadb.conf.d for innodb_buffer_pool_size (last value wins).
// Supports K/M/G suffixes. Returns 0 if the key is absent.
func ReadConfiguredBufferPoolSize() uint64 {
	dirs := []string{"/etc/mysql/conf.d", "/etc/mysql/mariadb.conf.d"}
	var result uint64
	for _, dir := range dirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		for _, e := range entries {
			if e.IsDir() || !strings.HasSuffix(e.Name(), ".cnf") {
				continue
			}
			f, err := os.Open(dir + "/" + e.Name())
			if err != nil {
				continue
			}
			inSection := false
			scanner := bufio.NewScanner(f)
			for scanner.Scan() {
				line := strings.TrimSpace(scanner.Text())
				if line == "" || line[0] == '#' || line[0] == ';' {
					continue
				}
				if line[0] == '[' {
					sec := strings.ToLower(strings.Trim(line, "[]"))
					inSection = sec == "mysqld" || sec == "mariadb" || sec == "server"
					continue
				}
				if !inSection {
					continue
				}
				eq := strings.IndexByte(line, '=')
				if eq < 0 {
					continue
				}
				k := strings.ReplaceAll(strings.TrimSpace(line[:eq]), "-", "_")
				if !strings.EqualFold(k, "innodb_buffer_pool_size") {
					continue
				}
				v := strings.TrimSpace(line[eq+1:])
				mul := uint64(1)
				switch strings.ToUpper(string(v[len(v)-1])) {
				case "K":
					mul, v = 1024, v[:len(v)-1]
				case "M":
					mul, v = 1024*1024, v[:len(v)-1]
				case "G":
					mul, v = 1024*1024*1024, v[:len(v)-1]
				}
				if n, err := strconv.ParseUint(strings.TrimSpace(v), 10, 64); err == nil {
					result = n * mul
				}
			}
			f.Close()
		}
	}
	return result
}

// InnoDBBufferPoolConfig holds static InnoDB buffer pool configuration.
type InnoDBBufferPoolConfig struct {
	Size          uint64
	ChunkSize     uint64
	Instances     uint64
	ResizeStatus  string
	ResizePending bool
}

// GetInnoDBBufferPoolConfig returns static InnoDB buffer pool configuration.
func (d *Database) GetInnoDBBufferPoolConfig() (InnoDBBufferPoolConfig, error) {
	vars, err := d.queryKVStr("SHOW GLOBAL VARIABLES")
	if err != nil {
		return InnoDBBufferPoolConfig{}, fmt.Errorf("SHOW GLOBAL VARIABLES: %w", err)
	}
	status, err := d.queryKVStr("SHOW GLOBAL STATUS")
	if err != nil {
		return InnoDBBufferPoolConfig{}, fmt.Errorf("SHOW GLOBAL STATUS: %w", err)
	}

	parseU := func(s string) uint64 {
		n, _ := strconv.ParseUint(s, 10, 64)
		return n
	}

	v := status["innodb_buffer_pool_resize_status"]
	return InnoDBBufferPoolConfig{
		Size:          parseU(vars["innodb_buffer_pool_size"]),
		ChunkSize:     parseU(vars["innodb_buffer_pool_chunk_size"]),
		Instances:     parseU(vars["innodb_buffer_pool_instances"]),
		ResizeStatus:  v,
		ResizePending: isPendingResizeStatus(v),
	}, nil
}

// isPendingResizeStatus returns true when the Innodb_buffer_pool_resize_status
// string indicates a resize is currently in flight.
func isPendingResizeStatus(v string) bool {
	for _, p := range []string{
		"Resizing buffer pool",
		"Withdrawing blocks",
		"Latching whole",
		"buffer pool",
		"Resizing",
	} {
		if strings.HasPrefix(v, p) {
			return true
		}
	}
	return false
}

// IsBufferPoolResizePending reports whether a resize is still in flight.
// Only known in-flight phase strings are treated as pending.
func (d *Database) IsBufferPoolResizePending() (bool, error) {
	status, err := d.queryKVStr("SHOW GLOBAL STATUS")
	if err != nil {
		return false, fmt.Errorf("SHOW GLOBAL STATUS: %w", err)
	}
	return isPendingResizeStatus(status["innodb_buffer_pool_resize_status"]), nil
}

// ResizeInnoDBBufferPool sets innodb_buffer_pool_size to the largest
// chunk_size*instances multiple <= requestedBytes. Errors if busy.
func (d *Database) ResizeInnoDBBufferPool(requestedBytes uint64) (uint64, error) {
	pending, err := d.IsBufferPoolResizePending()
	if err != nil {
		return 0, fmt.Errorf("check resize status: %w", err)
	}
	if pending {
		return 0, fmt.Errorf("innodb buffer pool resize already in progress")
	}

	cfg, err := d.GetInnoDBBufferPoolConfig()
	if err != nil {
		return 0, fmt.Errorf("get buffer pool config: %w", err)
	}

	chunkSize := cfg.ChunkSize
	if chunkSize == 0 {
		chunkSize = 128 << 20
	}
	instances := cfg.Instances
	if instances == 0 {
		instances = 1
	}

	unit := chunkSize * instances

	aligned := (requestedBytes / unit) * unit
	if aligned < unit {
		aligned = unit
	}

	err = d.execSocket("SET GLOBAL innodb_buffer_pool_size = " + strconv.FormatUint(aligned, 10))
	if err != nil {
		return 0, fmt.Errorf("set innodb_buffer_pool_size to %d: %w", aligned, err)
	}

	return aligned, nil
}
