package main

import (
	"fmt"
	"os"
	"strings"
)

func fileExists(filename string) bool {
	_, err := os.Stat(filename)
	return err == nil
}

func convertToStringSlice(slice any) []string {
	if s, ok := slice.([]any); ok {
		result := make([]string, len(s))
		for i, v := range s {
			if str, ok := v.(string); ok {
				result[i] = str
			}
		}
		return result
	}
	return nil
}

func getString(m map[string]any, key string) string {
	if val, ok := m[key].(string); ok {
		return val
	}
	return ""
}

func formatBytes(size int64) string {
	const unit = 1024
	if size < unit {
		return fmt.Sprintf("%d B", size)
	}
	div, exp := int64(unit), 0
	for n := size / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	units := []string{"KB", "MB", "GB", "TB", "PB", "EB"}
	if exp >= len(units) {
		exp = len(units) - 1
	}
	return fmt.Sprintf("%.1f %s", float64(size)/float64(div), units[exp])
}

func getTotalSize(m *MultipartUpload) int64 {
	if m == nil {
		return 0
	}
	// If database file is sql file, divide its size by 8 atleast
	if strings.HasSuffix(m.FileName, ".sql") {
		return m.TotalSize / 8
	}
	return m.TotalSize
}
