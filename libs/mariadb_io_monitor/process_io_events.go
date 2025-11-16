package main

import (
	"fmt"
	"strings"
	"sync"
	"time"
)

// EventKey uniquely identifies an I/O operation (aggregated by file)
type EventKey struct {
	Pid      uint32 // Process ID
	Op       uint8  // 'R' or 'W'
	Filename string // Full path
}

// TrackedEvent represents aggregated I/O operations on a file
type TrackedEvent struct {
	FirstOpTime   time.Time // When first operation started
	LastOpTime    time.Time // When last operation occurred
	TotalBytes    uint64    // Total bytes across all operations
	OperationCount uint64   // Total number of operations (Entry + Exit)
	EntryCount    uint64    // Number of entry events
	ExitCount     uint64    // Number of exit events
	PendingCount  int64     // Balance: entry events - exit events (stuck if > 0)

	Pid       uint32
	Op        uint8 // 'R' or 'W'
	Comm      string
	Directory string
	Filename  string
}

// EventTracker tracks aggregated I/O events from eBPF
type EventTracker struct {
	mu              sync.RWMutex
	aggregatedEvents map[EventKey]*TrackedEvent // Aggregated events per file
	maxEvents       int                         // Max events to track (5000)
	staleThreshold  time.Duration               // Remove if no activity for this long (1 hour)
	stuckThreshold  time.Duration               // Consider stuck if pending > 0 for this long (5s)
}

func NewEventTracker() *EventTracker {
	return &EventTracker{
		aggregatedEvents: make(map[EventKey]*TrackedEvent),
		maxEvents:        5000,
		staleThreshold:   1 * time.Hour,
		stuckThreshold:   5 * time.Second,
	}
}

// ProcessEvent handles incoming eBPF events and aggregates them
func (et *EventTracker) ProcessEvent(event eBPFEvent) {
	// Convert byte arrays to strings
	comm := strings.TrimRight(string(event.Comm[:]), "\x00")
	directory := strings.TrimRight(string(event.Directory[:]), "\x00")
	filename := strings.TrimRight(string(event.Filename[:]), "\x00")

	key := EventKey{
		Pid:      event.Pid,
		Op:       event.Op,
		Filename: filename,
	}

	et.mu.Lock()
	defer et.mu.Unlock()

	// Clean up stale events before processing
	et.cleanupStaleEventsLocked()

	// Get or create aggregated event
	tracked, exists := et.aggregatedEvents[key]
	if !exists {
		// Create new aggregated event
		tracked = &TrackedEvent{
			FirstOpTime:    time.Now(),
			LastOpTime:     time.Now(),
			TotalBytes:     0,
			OperationCount: 0,
			EntryCount:     0,
			ExitCount:      0,
			PendingCount:   0,
			Pid:            event.Pid,
			Op:             event.Op,
			Comm:           comm,
			Directory:      directory,
			Filename:       filename,
		}
		et.aggregatedEvents[key] = tracked
	}

	// Update aggregated stats
	tracked.LastOpTime = time.Now()
	tracked.TotalBytes += event.Bytes
	tracked.OperationCount++

	// Update entry/exit counts and balance
	if event.Stage == 'E' {
		tracked.EntryCount++
		tracked.PendingCount++ // Entry event
	} else if event.Stage == 'X' {
		tracked.ExitCount++
		tracked.PendingCount-- // Exit event
	}
}

// cleanupStaleEventsLocked removes events that haven't been active for > staleThreshold
// or if total events exceeds maxEvents (remove oldest)
// Must be called with lock held
func (et *EventTracker) cleanupStaleEventsLocked() {
	now := time.Now()

	// Remove stale events (no activity for 1 hour)
	for key, tracked := range et.aggregatedEvents {
		if now.Sub(tracked.LastOpTime) > et.staleThreshold {
			delete(et.aggregatedEvents, key)
		}
	}

	// If still over limit, remove oldest events
	if len(et.aggregatedEvents) > et.maxEvents {
		// Find and remove oldest events until under limit
		type eventWithKey struct {
			key   EventKey
			event *TrackedEvent
		}
		var events []eventWithKey
		for k, v := range et.aggregatedEvents {
			events = append(events, eventWithKey{k, v})
		}

		// Sort by LastOpTime (oldest first)
		for i := 0; i < len(events)-1; i++ {
			for j := i + 1; j < len(events); j++ {
				if events[i].event.LastOpTime.After(events[j].event.LastOpTime) {
					events[i], events[j] = events[j], events[i]
				}
			}
		}

		// Remove oldest until under limit
		removeCount := len(et.aggregatedEvents) - et.maxEvents
		for i := 0; i < removeCount; i++ {
			delete(et.aggregatedEvents, events[i].key)
		}
	}
}

// GetStuckOperations returns aggregated operations with pending count > 0 for > stuckThreshold
func (et *EventTracker) GetStuckOperations() []TrackedEvent {
	et.mu.RLock()
	defer et.mu.RUnlock()

	var stuck []TrackedEvent
	now := time.Now()

	for _, tracked := range et.aggregatedEvents {
		if tracked.PendingCount > 0 && now.Sub(tracked.FirstOpTime) > et.stuckThreshold {
			stuck = append(stuck, *tracked)
		}
	}

	return stuck
}

// GetMostActiveFiles returns the N files with most I/O activity
func (et *EventTracker) GetMostActiveFiles(n int) []TrackedEvent {
	et.mu.RLock()
	defer et.mu.RUnlock()

	var events []TrackedEvent
	for _, tracked := range et.aggregatedEvents {
		events = append(events, *tracked)
	}

	// Sort by operation count (descending)
	for i := 0; i < len(events)-1; i++ {
		for j := i + 1; j < len(events); j++ {
			if events[i].OperationCount < events[j].OperationCount {
				events[i], events[j] = events[j], events[i]
			}
		}
	}

	// Return top N
	if len(events) > n {
		events = events[:n]
	}

	return events
}

// GetStats returns summary statistics
func (et *EventTracker) GetStats() (totalTracked, totalStuck int, totalOps uint64) {
	et.mu.RLock()
	defer et.mu.RUnlock()

	totalTracked = len(et.aggregatedEvents)
	now := time.Now()

	for _, tracked := range et.aggregatedEvents {
		totalOps += tracked.OperationCount
		if tracked.PendingCount > 0 && now.Sub(tracked.FirstOpTime) > et.stuckThreshold {
			totalStuck++
		}
	}

	return
}

// Duration returns the time span from first to last operation
func (te *TrackedEvent) Duration() float64 {
	return te.LastOpTime.Sub(te.FirstOpTime).Seconds()
}

// AverageThroughput returns the average throughput in MB/s across all operations
func (te *TrackedEvent) AverageThroughput() float64 {
	duration := te.Duration()
	if duration <= 0 || te.TotalBytes == 0 {
		return 0
	}
	return (float64(te.TotalBytes) / duration) / (1024 * 1024) // MB/s
}

// TimeSinceLastOp returns how long ago the last operation occurred
func (te *TrackedEvent) TimeSinceLastOp() float64 {
	return time.Since(te.LastOpTime).Seconds()
}

// IsStuck returns whether the operation has imbalanced pending count
func (te *TrackedEvent) IsStuck() bool {
	return te.PendingCount > 0
}

// FormatEventForLog formats an aggregated tracked event for logging (tabular with filename)
func FormatEventForLog(te TrackedEvent) string {
	opName := "R"
	if te.Op == 'W' {
		opName = "W"
	}

	fullPath := te.Directory + "/" + te.Filename
	// Truncate long paths
	if len(fullPath) > 60 {
		fullPath = "..." + fullPath[len(fullPath)-57:]
	}

	if te.IsStuck() {
		return fmt.Sprintf("%-15s %1s %7d %7d %10.2f %10.2f %6d  STUCK  %s",
			te.Comm,
			opName,
			te.EntryCount,
			te.ExitCount,
			float64(te.TotalBytes)/1024/1024,
			te.AverageThroughput(),
			te.PendingCount,
			fullPath,
		)
	} else {
		return fmt.Sprintf("%-15s %1s %7d %7d %10.2f %10.2f %8.1f  %s",
			te.Comm,
			opName,
			te.EntryCount,
			te.ExitCount,
			float64(te.TotalBytes)/1024/1024,
			te.AverageThroughput(),
			te.Duration(),
			fullPath,
		)
	}
}

func (m *Monitor) ProcessBPFEvents() {
	m.wg.Add(1)
	defer m.wg.Done()

	for {
		select {
		case <-m.ctx.Done():
			fmt.Println("BPF Event Processor stopping:", m.ctx.Err())
			return
		case event := <-m.ebpfEventChan:
			if !m.enableEbpfEventCollection {
				continue
			}
			// Process the event through tracker
			m.eventTracker.ProcessEvent(event)
		}
	}
}
