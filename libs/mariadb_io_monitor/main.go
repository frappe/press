package main

//go:generate ./gen_bpf.sh

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

const (
	SampleInterval = 2 * time.Second // Every 2 seconds
	MaxSamples     = 600             // Keep last 600 samples (20 minutes at 2s interval)
	SectorSize     = 512
)

type Monitor struct {
	ctx           context.Context
	ctxCancel     context.CancelFunc
	wg            *sync.WaitGroup
	ebpfEventChan chan eBPFEvent
	sampler       *Sampler
	eventTracker  *EventTracker

	// There is no point in logging events if there is no anomaly

	enableEventLoggingInDisk  bool
	enableEbpfEventCollection bool

	// Anomaly detection state tracking
	lastWarningTime  time.Time
	lastCriticalTime time.Time

	// Logging configuration
	logFilePath    string
	logFile        *os.File
	logFileMu      sync.Mutex
	maxLogSize     int64
	truncateToSize int64
}

func (m *Monitor) Start() {
	go m.ListenToeBPFEvents()
	go m.StartStatsSampler()
	go m.ProcessStatSamples()
	go m.ProcessBPFEvents()
	go m.LogFindings()
}

func (m *Monitor) Stop() {
	m.ctxCancel()
}

func (m *Monitor) Wait() {
	m.wg.Wait()
}

func main() {
	ctx := context.Background()
	ctx, cancel := context.WithCancel(ctx)

	// Open log file for append-only writes
	logFilePath := "/var/log/mariadb_io_monitor.log"
	logFile, err := os.OpenFile(logFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		fmt.Printf("Failed to open log file: %v\n", err)
		os.Exit(1)
	}

	monitor := &Monitor{
		ctx:            ctx,
		ctxCancel:      cancel,
		wg:             &sync.WaitGroup{},
		ebpfEventChan:  make(chan eBPFEvent, 1000),
		sampler:        &Sampler{buf: NewCircularBuffer[StatsSample](MaxSamples)},
		eventTracker:   NewEventTracker(),
		logFilePath:    logFilePath,
		logFile:        logFile,
		maxLogSize:     50 * 1024 * 1024, // 50 MB
		truncateToSize: 30 * 1024 * 1024, // 30 MB

		enableEventLoggingInDisk:  true,
		enableEbpfEventCollection: true,
	}

	monitor.Start()

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	fmt.Println("\nReceived signal, shutting down...")
	monitor.Stop()

	monitor.Wait()

	// Close log file on shutdown
	if err := logFile.Close(); err != nil {
		fmt.Printf("Error closing log file: %v\n", err)
	}
	fmt.Println("Log file closed successfully")
}
