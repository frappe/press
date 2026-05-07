package main

import (
	"fmt"
	"strconv"
	"strings"
)

// InnoDBBufferPoolConfig holds static InnoDB buffer pool configuration.
type InnoDBBufferPoolConfig struct {
	Size         uint64
	ChunkSize    uint64
	Instances    uint64
	ResizeStatus string
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

	return InnoDBBufferPoolConfig{
		Size:         parseU(vars["innodb_buffer_pool_size"]),
		ChunkSize:    parseU(vars["innodb_buffer_pool_chunk_size"]),
		Instances:    parseU(vars["innodb_buffer_pool_instances"]),
		ResizeStatus: status["innodb_buffer_pool_resize_status"],
	}, nil
}

// IsBufferPoolResizePending reports whether a previous resize is still in flight.
func (d *Database) IsBufferPoolResizePending() (bool, error) {
	status, err := d.queryKVStr("SHOW GLOBAL STATUS")
	if err != nil {
		return false, fmt.Errorf("SHOW GLOBAL STATUS: %w", err)
	}
	v := status["innodb_buffer_pool_resize_status"]
	if v == "" || strings.HasPrefix(v, "Completed") {
		return false, nil
	}
	return true, nil
}

// ResizeInnoDBBufferPool sets innodb_buffer_pool_size to the largest
// chunk_size*instances multiple <= requestedBytes and returns the actual size.
// Errors if a resize is already in progress.
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
		chunkSize = 128 << 20 // 128 MiB default
	}
	instances := cfg.Instances
	if instances == 0 {
		instances = 1
	}

	unit := chunkSize * instances
	if requestedBytes < unit {
		return 0, fmt.Errorf("requested size %d is less than minimum unit %d (chunk_size %d * instances %d)",
			requestedBytes, unit, chunkSize, instances)
	}

	aligned := (requestedBytes / unit) * unit

	err = d.execSocket("SET GLOBAL innodb_buffer_pool_size = " + strconv.FormatUint(aligned, 10))
	if err != nil {
		return 0, fmt.Errorf("set innodb_buffer_pool_size to %d: %w", aligned, err)
	}

	return aligned, nil
}
