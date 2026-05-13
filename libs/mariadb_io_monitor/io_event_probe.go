package main

import (
	"bytes"
	"context"
	"encoding/binary"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/link"
	"github.com/cilium/ebpf/perf"
	"github.com/shirou/gopsutil/process"
)

// ebpf eBPFEvent
type eBPFEvent struct {
	Pid       uint32
	Tid       uint32
	Op        uint8 // 'R' or 'W'
	Stage     uint8 // 'E' or 'X'
	Pad       [6]byte
	Bytes     uint64
	Comm      [32]byte
	Directory [128]byte
	Filename  [128]byte
}

func (m *Monitor) ListenToeBPFEvents() {
	objs := io_traceObjects{}
	if err := loadIo_traceObjects(&objs, nil); err != nil {
		log.Fatalf("loading objects: %v", err)
	}

	// Attach both read and write kprobes
	writeKprobe, err := link.Kprobe("vfs_write", objs.KprobeVfsWrite, nil)
	if err != nil {
		objs.Close()
		log.Fatalf("attach kprobe vfs_write: %v", err)
	}
	defer writeKprobe.Close()

	readKprobe, err := link.Kprobe("vfs_read", objs.KprobeVfsRead, nil)
	if err != nil {
		writeKprobe.Close()
		objs.Close()
		log.Fatalf("attach kprobe vfs_read: %v", err)
	}
	defer readKprobe.Close()

	writeKRetprobe, err := link.Kretprobe("vfs_write", objs.KretprobeVfsWrite, nil)
	if err != nil {
		readKprobe.Close()
		writeKprobe.Close()
		objs.Close()
		log.Fatalf("attach kretprobe vfs_write: %v", err)
	}
	defer writeKRetprobe.Close()

	readKRetprobe, err := link.Kretprobe("vfs_read", objs.KretprobeVfsRead, nil)
	if err != nil {
		writeKRetprobe.Close()
		readKprobe.Close()
		writeKprobe.Close()
		objs.Close()
		log.Fatalf("attach kretprobe vfs_read: %v", err)
	}
	defer readKRetprobe.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start different goroutines to track MariaDB PIDs and monitor tracking state
	if err := monitorMariadbPIDsAndUpdate(ctx, m.wg, &objs); err != nil {
		log.Fatalf("failed to start monitor: %v", err)
	}

	monitorTrackingState(ctx, m.wg, &objs, m)

	// Set up perf reader
	// Each event is 320 bytes, so it can hold around 800 events in buffer
	rd, err := perf.NewReader(objs.Events, os.Getpagesize()*64)
	if err != nil {
		log.Fatalf("creating perf reader: %v", err)
	}
	defer rd.Close()

	m.wg.Add(1)
	go func() {
		defer m.wg.Done()
		var e eBPFEvent

		for {
			record, err := rd.Read()
			if err != nil {
				if isPerfClosedError(err) {
					return
				}
				log.Printf("read error: %v", err)
				time.Sleep(50 * time.Millisecond)
				continue
			}

			if record.LostSamples != 0 {
				log.Printf("lost %d samples", record.LostSamples)
				continue
			}

			// Check if channel is closd
			if m.ebpfEventChan == nil {
				return
			}

			if err := binary.Read(bytes.NewReader(record.RawSample), binary.LittleEndian, &e); err != nil {
				log.Printf("parsing event: %v", err)
				continue
			}

			m.ebpfEventChan <- e
		}
	}()

	<-m.ctx.Done()
	log.Println("shutting down monitor...")

	if err := rd.Close(); err != nil {
		log.Printf("error closing perf reader: %v", err)
	}

	// cleanup BPF side
	if err := objs.Close(); err != nil {
		log.Printf("warning closing bpf objects: %v", err)
	}

	fmt.Println("Shutdown complete.")
}

func monitorMariadbPIDsAndUpdate(ctx context.Context, wg *sync.WaitGroup, objs *io_traceObjects) error {
	// sanity checks
	if ctx == nil {
		return fmt.Errorf("nil context")
	}
	if objs == nil || objs.Pids == nil {
		return fmt.Errorf("objs or objs.Pids is nil")
	}

	const pollInterval = 5 * time.Second
	const mapValue = uint8(1)

	// helper to collect current mariadb PIDs
	fetchMariadb := func() (map[uint32]struct{}, error) {
		procs, err := process.Processes()
		if err != nil {
			return nil, fmt.Errorf("getting processes: %w", err)
		}
		out := make(map[uint32]struct{})
		for _, p := range procs {
			name, err := p.Name()
			if err != nil {
				continue
			}

			if strings.Compare(strings.ToLower(strings.TrimSpace(name)), "mariadbd") == 0 {
				out[uint32(p.Pid)] = struct{}{}
			}
		}
		return out, nil
	}

	// initial population of the eBPF map
	initial, err := fetchMariadb()
	if err != nil {
		return err
	}
	for pid := range initial {
		if err := objs.Pids.Update(pid, mapValue, ebpf.UpdateAny); err != nil {
			log.Printf("warning: failed to add initial pid %d: %v", pid, err)
		} else {
			log.Printf("tracking pid %d (initial)", pid)
		}
	}

	// maintain an in-memory set of tracked PIDs for quick reference (optional but kept here per request)
	tracked := make(map[uint32]struct{}, len(initial))
	for pid := range initial {
		tracked[pid] = struct{}{}
	}

	ticker := time.NewTicker(pollInterval)
	wg.Add(1)
	go func() {
		defer wg.Done()
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				log.Printf("MonitorMariadbPIDs stopping: %v", ctx.Err())
				return
			case <-ticker.C:
				newSet, err := fetchMariadb()
				if err != nil {
					log.Printf("error fetching mariadb pids: %v", err)
					continue
				}

				// Read current keys from eBPF map to ensure we remove any keys that might not be in tracked (robustness)
				existing := make(map[uint32]struct{})
				var k uint32
				var v uint8
				it := objs.Pids.Iterate()
				for it.Next(&k, &v) {
					existing[k] = struct{}{}
				}
				if err := it.Err(); err != nil {
					log.Printf("error iterating ebpf map: %v", err)
				}

				// Delete stale keys: those present in existing but not in newSet
				for pid := range existing {
					if _, keep := newSet[pid]; !keep {
						if err := objs.Pids.Delete(pid); err != nil {
							log.Printf("failed to delete stale pid %d: %v", pid, err)
						} else {
							delete(tracked, pid)
							log.Printf("stopped tracking pid %d (deleted)", pid)
						}
					}
				}

				// Add new keys: those in newSet but not present in existing
				for pid := range newSet {
					if _, present := existing[pid]; present {
						// already in map
						if _, t := tracked[pid]; !t {
							// ensure in-memory tracked stays consistent
							tracked[pid] = struct{}{}
						}
						continue
					}
					if err := objs.Pids.Update(pid, mapValue, ebpf.UpdateAny); err != nil {
						log.Printf("failed to add pid %d: %v", pid, err)
					} else {
						tracked[pid] = struct{}{}
						log.Printf("tracking pid %d (added)", pid)
					}
				}
			}
		}
	}()

	return nil
}

func monitorTrackingState(ctx context.Context, wg *sync.WaitGroup, objs *io_traceObjects, monitor *Monitor) {
	const checkInterval = 1 * time.Second

	ticker := time.NewTicker(checkInterval)
	wg.Add(1)
	go func() {
		defer wg.Done()
		defer ticker.Stop()

		enabled := false

		for {
			select {
			case <-ctx.Done():
				log.Printf("monitorTrackingState stopping: %v", ctx.Err())
				return
			case <-ticker.C:
				shouldEnable := monitor.enableEbpfEventCollection
				if shouldEnable && !enabled {
					// Enable processing
					val := uint8(1)
					if err := objs.GlobalProcessingFlag.Update(uint32(0), val, ebpf.UpdateAny); err != nil {
						log.Printf("failed to enable global processing in eBPF: %v", err)
					} else {
						enabled = true
						log.Println("eBPF global processing ENABLED")
					}
				} else if !shouldEnable && enabled {
					// Disable processing
					val := uint8(0)
					if err := objs.GlobalProcessingFlag.Update(uint32(0), val, ebpf.UpdateAny); err != nil {
						log.Printf("failed to disable global processing in eBPF: %v", err)
					} else {
						enabled = false
						log.Println("eBPF global processing DISABLED")
					}
				}
			}
		}
	}()
}
