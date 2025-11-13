package main

import (
	"fmt"
	"time"
)

// Cooldown periods - prevent rapid state flapping
const (
	WarningCooldown  = 30 * time.Second // Stay in WARNING for at least 30s
	CriticalCooldown = 60 * time.Second // Stay in CRITICAL for at least 60s
)

const (
	// CRITICAL: Full PSI - all non-idle tasks stalled (queries blocked)
	PSI_IO_Full_Critical     = 5.0 // % - queries waiting on disk I/O
	PSI_Memory_Full_Critical = 3.0 // % - should rarely happen with proper buffer pool
	PSI_CPU_Full_Critical    = 8.0 // % - all queries blocked on CPU (rare)

	// WARNING: Some PSI - early pressure detection for query performance
	PSI_IO_Some_Warning     = 15.0 // % - catch I/O pressure early (NVMe should be fast)
	PSI_IO_Full_Warning     = 2.0  // % - any full I/O stall is concerning for DB
	PSI_Memory_Some_Warning = 25.0 // % - memory contention beyond buffer pool
	PSI_CPU_Some_Warning    = 40.0 // % - query concurrency issues
)

// CPU Thresholds
const (
	IOWait_Warning  = 15.0 // % - early sign of disk becoming bottleneck
	IOWait_Critical = 30.0 // % - severe I/O bottleneck, queries delayed
)

// Memory Thresholds
const (
	Memory_Usage_Warning  = 90.0 // % - non-buffer memory filling up
	Memory_Usage_Critical = 98.0 // % - risk of OOM killer, potential buffer pool eviction
)

// Swap Activity Thresholds
const (
	Swap_Rate_Warning  = 50.0  // pages/sec - LOW threshold, databases should not swap
	Swap_Rate_Critical = 200.0 // pages/sec - heavy thrashing, queries grinding to halt
)

// Disk I/O Thresholds - NVMe SSD specific
const (
	Disk_Latency_Warning    = 10.0 // milliseconds - slow for NVMe, affects query performance
	Disk_Latency_Critical   = 25.0 // milliseconds - very slow for NVMe, serious bottleneck
	Disk_QueueDepth_Warning = 16.0 // Queue building up on fast NVMe = saturation
)

// CheckWarningConditions checks if any WARNING-level thresholds are exceeded
func (m *Monitor) CheckWarningConditions(sample StatsSample) bool {
	// PSI Warning levels - early I/O pressure detection
	if sample.PSI.IO_SomeAvg10 > PSI_IO_Some_Warning {
		return true
	}
	// Any "full" I/O stall is a warning for databases
	if sample.PSI.IO_FullAvg10 > PSI_IO_Full_Warning {
		fmt.Println("PSI I/O Full Warning triggered")
		return true
	}
	if sample.PSI.Memory_SomeAvg10 > PSI_Memory_Some_Warning {
		return true
	}
	if sample.PSI.CPU_SomeAvg10 > PSI_CPU_Some_Warning {
		return true
	}

	// CPU IOWait warning - lower threshold for DB workloads
	if sample.CPU.IOwaitPercent > IOWait_Warning {
		return true
	}

	// Memory usage warning - adjusted for 70% InnoDB buffer pool allocation
	if sample.Memory.TotalBytes > 0 {
		memUsagePercent := float64(sample.Memory.ActualUsedBytes) / float64(sample.Memory.TotalBytes) * 100.0
		if memUsagePercent > Memory_Usage_Warning {
			fmt.Println("Memory usage warning triggered")
			return true
		}
	}

	// Swap activity warning - databases should NOT swap
	if sample.Swap.PageInPerSecond > Swap_Rate_Warning || sample.Swap.PageOutPerSecond > Swap_Rate_Warning {
		fmt.Println("Swap activity warning triggered")
		return true
	}

	// Disk latency warning - NVMe specific, lower threshold
	if sample.Disk.ReadLatencyMillis > Disk_Latency_Warning || sample.Disk.WriteLatencyMillis > Disk_Latency_Warning {
		fmt.Println("Disk latency warning triggered")
		return true
	}

	// Queue depth warning - indicates NVMe saturation
	if sample.Disk.QueueDepth > Disk_QueueDepth_Warning {
		fmt.Println("Disk queue depth warning triggered")
		return true
	}

	return false
}

// CheckCriticalConditions checks if any CRITICAL-level thresholds are exceeded
func (m *Monitor) CheckCriticalConditions(sample StatsSample) bool {
	// PSI Critical levels - queries are blocked
	if sample.PSI.IO_FullAvg10 > PSI_IO_Full_Critical {
		return true
	}
	if sample.PSI.Memory_FullAvg10 > PSI_Memory_Full_Critical {
		return true
	}
	if sample.PSI.CPU_FullAvg10 > PSI_CPU_Full_Critical {
		return true
	}

	// CPU IOWait critical - severe disk bottleneck
	if sample.CPU.IOwaitPercent > IOWait_Critical {
		return true
	}

	// Memory usage critical - risk of OOM affecting buffer pool
	if sample.Memory.TotalBytes > 0 {
		memUsagePercent := float64(sample.Memory.ActualUsedBytes) / float64(sample.Memory.TotalBytes) * 100.0
		if memUsagePercent > Memory_Usage_Critical {
			return true
		}
	}

	// Heavy swap thrashing - catastrophic for database
	if sample.Swap.PageInPerSecond > Swap_Rate_Critical || sample.Swap.PageOutPerSecond > Swap_Rate_Critical {
		return true
	}

	// Severe disk latency - NVMe performing like HDD
	if sample.Disk.ReadLatencyMillis > Disk_Latency_Critical || sample.Disk.WriteLatencyMillis > Disk_Latency_Critical {
		return true
	}

	return false
}

// UpdateAnomalyState checks current conditions and updates Monitor flags with cooldown logic
func (m *Monitor) UpdateAnomalyState(sample StatsSample) {
	now := time.Now()

	// Check current conditions
	currentlyWarning := m.CheckWarningConditions(sample)
	currentlyCritical := m.CheckCriticalConditions(sample)

	// Update timestamps if conditions are met
	if currentlyCritical {
		m.lastCriticalTime = now
	}
	if currentlyWarning {
		m.lastWarningTime = now
	}

	// Apply cooldown logic - stay in state for minimum duration
	criticalActive := now.Sub(m.lastCriticalTime) < CriticalCooldown
	warningActive := now.Sub(m.lastWarningTime) < WarningCooldown

	defer func() {
		fmt.Printf("Anomaly State Updated - WARNING Active: %v, CRITICAL Active: %v\n", warningActive, criticalActive)
	}()

	// Set flags based on active states
	// CRITICAL implies both logging AND eBPF collection
	if criticalActive {
		m.enableEventLoggingInDisk = true
		m.enableEbpfEventCollection = true
		return
	}

	// WARNING implies only eBPF collection (no logging yet)
	if warningActive {
		m.enableEventLoggingInDisk = false
		m.enableEbpfEventCollection = true
		return
	}

	// Normal state - clear both flags
	m.enableEventLoggingInDisk = false
	m.enableEbpfEventCollection = false
}
