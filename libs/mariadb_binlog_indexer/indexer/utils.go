package main

import (
	"fmt"
	"os"
	"strconv"
)

const NO_OF_QUERIES_IN_EACH_PARQUET_PAGE = 4000

// EstimateParquetPageSize returns a reasonable page size based on binlog file size
// This avoids parsing the entire binlog twice, reducing memory usage significantly
func EstimateParquetPageSize(binlogPath string) (int64, error) {
	info, err := os.Stat(binlogPath)
	if err != nil {
		return 0, fmt.Errorf("failed to stat binlog file: %w", err)
	}

	fileSizeInMB := info.Size() / 1024 / 1024

	// Use a heuristic based on file size to avoid double-parsing
	// Smaller files: larger page size (less overhead)
	// Larger files: smaller page size (better memory management)
	var pageSize int64
	switch {
	case fileSizeInMB < 10:
		pageSize = 2 * 1024 * 1024 // 2MB
	case fileSizeInMB < 100:
		pageSize = 1 * 1024 * 1024 // 1MB
	case fileSizeInMB < 500:
		pageSize = 768 * 1024 // 768KB
	default:
		pageSize = 512 * 1024 // 512KB
	}

	return pageSize, nil
}

// itoa is a faster integer to string conversion for SQL building
func itoa(i int) string {
	return strconv.Itoa(i)
}
