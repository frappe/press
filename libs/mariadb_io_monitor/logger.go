package main

import (
	"fmt"
	"io"
	"os"
	"time"
)

func (m *Monitor) LogFindings() {
	m.wg.Add(1)
	defer m.wg.Done()

	ticker := time.NewTicker(7 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-m.ctx.Done():
			println("Logger stopping:", m.ctx.Err())
			return
		case <-ticker.C:
			if m.enableEventLoggingInDisk {
				m.logFindings()
			}
		}
	}
}

func (m *Monitor) logFindings() {
	now := time.Now()

	// Check and truncate file if needed
	if err := m.checkAndTruncateLog(); err != nil {
		fmt.Printf("Failed to truncate log: %v\n", err)
		return
	}

	// Capture MariaDB processlist
	mariadbProcessList, err := captureMariaDBProcessList()
	if err != nil {
		fmt.Printf("Failed to capture MariaDB processlist: %v\n", err)
	}

	// Get latest stats sample
	latestPtr := m.sampler.buf.GetLatest()
	if latestPtr == nil {
		fmt.Println("No stats samples available yet")
		return
	}
	latest := *latestPtr

	// Get last 10 samples for aggregates
	allSamples := m.sampler.buf.Snapshot()
	recentSamples := allSamples
	if len(allSamples) > 10 {
		recentSamples = allSamples[len(allSamples)-10:]
	}

	// Build log entry
	m.logFileMu.Lock()
	defer m.logFileMu.Unlock()

	// Write separator
	fmt.Fprintf(m.logFile, "\n")
	fmt.Fprintf(m.logFile, "ANOMALY SNAPSHOT\n")
	fmt.Fprintf(m.logFile, "Timestamp: %s\n", now.Format("2006-01-02 15:04:05"))
	fmt.Fprintf(m.logFile, "\n")

	// Latest Stats Sample
	fmt.Fprintf(m.logFile, "LATEST SYSTEM STATS\n")
	fmt.Fprintf(m.logFile, "Sample Time: %s\n", latest.Timestamp.Format("15:04:05"))
	fmt.Fprintf(m.logFile, "\nCPU:\n")
	fmt.Fprintf(m.logFile, "  User: %.2f%% | System: %.2f%% | IOWait: %.2f%% | Idle: %.2f%%\n",
		latest.CPU.UserPercent, latest.CPU.SystemPercent, latest.CPU.IOwaitPercent, latest.CPU.IdlePercent)

	fmt.Fprintf(m.logFile, "\nMemory:\n")
	fmt.Fprintf(m.logFile, "  Total: %.2f GB | Used: %.2f GB | Cache: %.2f GB\n",
		float64(latest.Memory.TotalBytes)/1e9,
		float64(latest.Memory.ActualUsedBytes)/1e9,
		float64(latest.Memory.CacheBytes)/1e9)
	fmt.Fprintf(m.logFile, "  Usage: %.2f%%\n",
		float64(latest.Memory.ActualUsedBytes)/float64(latest.Memory.TotalBytes)*100)

	fmt.Fprintf(m.logFile, "\nSwap:\n")
	fmt.Fprintf(m.logFile, "  Used: %.2f MB | PageIn: %.2f/s | PageOut: %.2f/s\n",
		float64(latest.Swap.UsedBytes)/1024/1024,
		latest.Swap.PageInPerSecond,
		latest.Swap.PageOutPerSecond)

	fmt.Fprintf(m.logFile, "\nDisk I/O:\n")
	fmt.Fprintf(m.logFile, "  Read: %.2f MB/s (%.2f IOPS, %.2fms latency)\n",
		latest.Disk.ReadThroughputBytes/1024/1024,
		latest.Disk.ReadIOPS,
		latest.Disk.ReadLatencyMillis)
	fmt.Fprintf(m.logFile, "  Write: %.2f MB/s (%.2f IOPS, %.2fms latency)\n",
		latest.Disk.WriteThroughputBytes/1024/1024,
		latest.Disk.WriteIOPS,
		latest.Disk.WriteLatencyMillis)
	fmt.Fprintf(m.logFile, "  Queue Depth: %.2f\n", latest.Disk.QueueDepth)

	fmt.Fprintf(m.logFile, "\nPSI (Pressure Stall Information):\n")
	fmt.Fprintf(m.logFile, "  I/O: Some=%.2f%% Full=%.2f%%\n",
		latest.PSI.IO_SomeAvg10, latest.PSI.IO_FullAvg10)
	fmt.Fprintf(m.logFile, "  Memory: Some=%.2f%% Full=%.2f%%\n",
		latest.PSI.Memory_SomeAvg10, latest.PSI.Memory_FullAvg10)
	fmt.Fprintf(m.logFile, "  CPU: Some=%.2f%% Full=%.2f%%\n",
		latest.PSI.CPU_SomeAvg10, latest.PSI.CPU_FullAvg10)

	// Aggregated Stats (Last 10 samples)
	fmt.Fprintf(m.logFile, "\nAGGREGATED STATS (Last %d samples, ~%d seconds)\n",
		len(recentSamples), len(recentSamples)*2)

	avgIOWait := 0.0
	avgMemUsage := 0.0
	avgSwapIn := 0.0
	avgSwapOut := 0.0
	avgReadLatency := 0.0
	avgWriteLatency := 0.0
	avgPSI_IO_Some := 0.0
	avgPSI_IO_Full := 0.0

	for _, s := range recentSamples {
		avgIOWait += s.CPU.IOwaitPercent
		if s.Memory.TotalBytes > 0 {
			avgMemUsage += float64(s.Memory.ActualUsedBytes) / float64(s.Memory.TotalBytes) * 100
		}
		avgSwapIn += s.Swap.PageInPerSecond
		avgSwapOut += s.Swap.PageOutPerSecond
		avgReadLatency += s.Disk.ReadLatencyMillis
		avgWriteLatency += s.Disk.WriteLatencyMillis
		avgPSI_IO_Some += s.PSI.IO_SomeAvg10
		avgPSI_IO_Full += s.PSI.IO_FullAvg10
	}

	count := float64(len(recentSamples))
	if count > 0 {
		fmt.Fprintf(m.logFile, "  Avg CPU IOWait: %.2f%%\n", avgIOWait/count)
		fmt.Fprintf(m.logFile, "  Avg Memory Usage: %.2f%%\n", avgMemUsage/count)
		fmt.Fprintf(m.logFile, "  Avg Swap In/Out: %.2f / %.2f pages/s\n", avgSwapIn/count, avgSwapOut/count)
		fmt.Fprintf(m.logFile, "  Avg Disk Latency: Read=%.2fms Write=%.2fms\n",
			avgReadLatency/count, avgWriteLatency/count)
		fmt.Fprintf(m.logFile, "  Avg PSI I/O: Some=%.2f%% Full=%.2f%%\n",
			avgPSI_IO_Some/count, avgPSI_IO_Full/count)
	}

	// Top Processes
	fmt.Fprintf(m.logFile, "\nTOP PROCESSES\n")
	fmt.Fprintf(m.logFile, "Top Memory Consumers:\n")
	for i, proc := range latest.TopMemoryProcesses {
		if i >= 5 {
			break
		}
		fmt.Fprintf(m.logFile, "  %d. %s: %.2f MB\n", i+1, proc.Name, float64(proc.Usage)/1024/1024)
	}

	fmt.Fprintf(m.logFile, "\nTop CPU Consumers:\n")
	for i, proc := range latest.TopCPUProcesses {
		if i >= 5 {
			break
		}
		fmt.Fprintf(m.logFile, "  %d. %s: %.2f%%\n", i+1, proc.Name, float64(proc.Usage)/100)
	}

	// MariaDB Process List
	if mariadbProcessList != "" {
		fmt.Fprintf(m.logFile, "\nMARIADB PROCESS LIST\n")
		fmt.Fprintf(m.logFile, "%s\n", mariadbProcessList)
	} else {
		fmt.Fprintf(m.logFile, "\nMARIADB PROCESS LIST\n")
		fmt.Fprintf(m.logFile, "(Not available)\n")
	}

	// eBPF Event Statistics
	fmt.Fprintf(m.logFile, "\nEBPF EVENTS (Aggregated by File)\n")
	totalTracked, stuckCount, totalOps := m.eventTracker.GetStats()
	fmt.Fprintf(m.logFile, "Files Tracked: %d | Total Operations: %d | Stuck Files: %d\n",
		totalTracked, totalOps, stuckCount)

	// Show stuck operations first (most important)
	stuckOps := m.eventTracker.GetStuckOperations()
	if len(stuckOps) > 0 {
		fmt.Fprintf(m.logFile, "\nSTUCK FILES (pending imbalance >5s):\n")
		fmt.Fprintf(m.logFile, "%-15s %1s %7s %7s %10s %10s %6s  %s  %s\n",
			"Process", "O", "Entry", "Exit", "TotalMB", "MB/s", "Pend", "Status", "File")
		fmt.Fprintf(m.logFile, "%-15s %1s %7s %7s %10s %10s %6s  %s  %s\n",
			"---------------", "-", "-------", "-------", "----------", "----------", "------", "------", "----")
		for i, op := range stuckOps {
			if i >= 10 {
				fmt.Fprintf(m.logFile, "... and %d more stuck files\n", len(stuckOps)-10)
				break
			}
			fmt.Fprintf(m.logFile, "%s\n", FormatEventForLog(op))
		}
	}

	// Show most active files (top 20 by operation count)
	activeFiles := m.eventTracker.GetMostActiveFiles(20)
	if len(activeFiles) > 0 {
		fmt.Fprintf(m.logFile, "\nMOST ACTIVE FILES (top 20 by operation count):\n")
		fmt.Fprintf(m.logFile, "%-15s %1s %7s %7s %10s %10s %8s  %s\n",
			"Process", "O", "Entry", "Exit", "TotalMB", "MB/s", "Duration", "File")
		fmt.Fprintf(m.logFile, "%-15s %1s %7s %7s %10s %10s %8s  %s\n",
			"---------------", "-", "-------", "-------", "----------", "----------", "--------", "----")
		for i, event := range activeFiles {
			if i >= 20 {
				break
			}
			fmt.Fprintf(m.logFile, "%s\n", FormatEventForLog(event))
		}
	}

	// Closing separator
	fmt.Fprintf(m.logFile, "\n================================================================================\n")
}

// checkAndTruncateLog checks if log file exceeds maxLogSize and truncates to truncateToSize
func (m *Monitor) checkAndTruncateLog() error {
	m.logFileMu.Lock()
	defer m.logFileMu.Unlock()

	// Get current file size
	info, err := m.logFile.Stat()
	if err != nil {
		return fmt.Errorf("failed to stat log file: %w", err)
	}

	// Check if truncation is needed
	if info.Size() < m.maxLogSize {
		return nil // No truncation needed
	}

	fmt.Printf("Log file size %.2f MB exceeds limit, truncating to %.2f MB...\n",
		float64(info.Size())/1024/1024,
		float64(m.truncateToSize)/1024/1024)

	// Close current file
	if err := m.logFile.Close(); err != nil {
		return fmt.Errorf("failed to close log file: %w", err)
	}

	// Open file for reading
	f, err := os.Open(m.logFilePath)
	if err != nil {
		// Reopen original file in append mode if this fails
		m.logFile, _ = os.OpenFile(m.logFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		return fmt.Errorf("failed to open log file for reading: %w", err)
	}

	// Calculate offset to keep last truncateToSize bytes
	offset := info.Size() - m.truncateToSize
	if offset < 0 {
		offset = 0
	}

	// Seek to offset
	if _, err := f.Seek(offset, io.SeekStart); err != nil {
		f.Close()
		m.logFile, _ = os.OpenFile(m.logFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		return fmt.Errorf("failed to seek in log file: %w", err)
	}

	// Read remaining data into memory
	remainingData, err := io.ReadAll(f)
	f.Close()
	if err != nil {
		m.logFile, _ = os.OpenFile(m.logFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		return fmt.Errorf("failed to read log file: %w", err)
	}

	// Truncate file and write back the last portion
	if err := os.WriteFile(m.logFilePath, remainingData, 0644); err != nil {
		m.logFile, _ = os.OpenFile(m.logFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		return fmt.Errorf("failed to write truncated log: %w", err)
	}

	// Reopen in append mode
	m.logFile, err = os.OpenFile(m.logFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("failed to reopen log file: %w", err)
	}

	fmt.Printf("Log file truncated successfully. New size: %.2f MB\n",
		float64(len(remainingData))/1024/1024)

	return nil
}
