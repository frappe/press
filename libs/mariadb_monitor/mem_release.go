package main

import (
	"context"
	"log/slog"
	"os/exec"
	"time"
)

// tryRelieveMemoryPressure performs soft, non-restart memory recovery in three
// stages: tcmalloc release, InnoDB buffer pool reduction, and forced swap
// reclaim. Returns true if any stage took action and the original InnoDB buffer
// pool size if it was reduced (0 otherwise).
func tryRelieveMemoryPressure(cfg Config, creds MySQLCredentials) (bool, uint64) {
	slog.Info("attempting soft memory pressure relief")
	relieved := false
	var originalBufferSize uint64

	db := NewDatabase(creds)

	if ok, err := db.Tcmalloc.IsAvailable(); err == nil && ok {
		stats, err := db.Tcmalloc.Stats()
		if err == nil {
			freeInTcmalloc := stats.HeapSize - stats.AllocatedBytes
			thresholdBytes := cfg.Release.TcmallocThresholdMB * 1024 * 1024
			if freeInTcmalloc > thresholdBytes {
				released, err := db.Tcmalloc.ReleaseMemory()
				if err == nil {
					slog.Info("tcmalloc released memory to OS",
						"released_bytes", released,
						"was_free_bytes", freeInTcmalloc,
					)
					relieved = true
				} else {
					slog.Warn("tcmalloc release failed", "error", err)
				}
			} else {
				slog.Debug("tcmalloc free memory below threshold, skipping release",
					"free_mb", freeInTcmalloc/1024/1024,
					"threshold_mb", cfg.Release.TcmallocThresholdMB,
				)
			}
		} else {
			slog.Warn("failed to read tcmalloc stats", "error", err)
		}
	}

	// InnoDB buffer pool reduction.
	mem, memErr := checkMemory()
	if memErr != nil {
		slog.Warn("memory release: failed to read /proc/meminfo", "error", memErr)
	} else {
		availableBytes := mem.MemAvailable * 1024
		minFreeBytes := cfg.Release.MinFreeMB * 1024 * 1024

		if availableBytes < minFreeBytes {
			deficit := minFreeBytes - availableBytes
			slog.Info("insufficient free memory, reducing InnoDB buffer pool",
				"available_mb", mem.MemAvailable/1024,
				"target_free_mb", cfg.Release.MinFreeMB,
				"deficit_mb", deficit/1024/1024,
			)

			bpCfg, err := db.GetInnoDBBufferPoolConfig()
			if err != nil {
				slog.Warn("memory release: failed to get buffer pool config", "error", err)
			} else {
				minBufBytes := cfg.Release.InnoDBBufferMinMB * 1024 * 1024
				currentSize := bpCfg.Size

				// Add headroom so we don't immediately re-enter the deficit.
				headroom := minFreeBytes / 4

				var targetSize uint64
				if deficit+headroom >= currentSize {
					targetSize = minBufBytes
				} else {
					targetSize = currentSize - deficit - headroom
					if targetSize < minBufBytes {
						targetSize = minBufBytes
					}
				}

				if targetSize < currentSize {
					actual, err := db.ResizeInnoDBBufferPool(targetSize)
					if err != nil {
						slog.Warn("memory release: buffer pool resize failed",
							"error", err,
							"current_mb", currentSize/1024/1024,
							"target_mb", targetSize/1024/1024,
						)
					} else {
						slog.Info("memory release: reduced InnoDB buffer pool",
							"from_mb", currentSize/1024/1024,
							"to_mb", actual/1024/1024,
							"freed_approx_mb", (currentSize-actual)/1024/1024,
						)
						originalBufferSize = currentSize
						relieved = true
					}
				} else {
					slog.Info("memory release: InnoDB buffer pool already at minimum, cannot reduce further",
						"current_mb", currentSize/1024/1024,
						"min_mb", minBufBytes/1024/1024,
					)
				}
			}
		} else {
			slog.Debug("memory release: sufficient free memory, skipping buffer reduction",
				"available_mb", mem.MemAvailable/1024,
				"target_free_mb", cfg.Release.MinFreeMB,
			)
		}
	}

	// Force swap reclaim if MariaDB is using enough swap and the system can absorb it.
	cgMem := readCgroupMemory()
	swapMinBytes := cfg.Release.SwapMinMB * 1024 * 1024
	if cgMem.SwapUsage > swapMinBytes {
		slog.Info("mariadb cgroup swap exceeds threshold, checking if safe to force swap reclaim",
			"mariadb_swap_mb", cgMem.SwapUsage/1024/1024,
			"threshold_mb", cfg.Release.SwapMinMB,
		)

		// Re-read memory after upstream actions may have freed RAM.
		if mem2, err := checkMemory(); err == nil {
			availableNow := mem2.MemAvailable * 1024
			totalSwapUsed := (mem2.SwapTotal - mem2.SwapFree) * 1024
			if totalSwapUsed > 0 && availableNow > totalSwapUsed {
				slog.Info("sufficient free RAM to absorb swap, forcing swap reclaim",
					"available_mb", availableNow/1024/1024,
					"total_swap_used_mb", totalSwapUsed/1024/1024,
				)
				forceSwapReclaim()
			} else {
				slog.Warn("not enough free RAM to safely swapoff, skipping swap reclaim",
					"available_mb", availableNow/1024/1024,
					"total_swap_used_mb", totalSwapUsed/1024/1024,
				)
			}
		}
	}

	if relieved {
		slog.Info("soft memory pressure relief completed")
	} else {
		slog.Info("soft memory pressure relief: no actions were necessary")
	}

	return relieved, originalBufferSize
}

// forceSwapReclaim runs swapoff -a then swapon -a to force the kernel to page
// swapped-out memory back into RAM. Caller must verify sufficient free RAM.
func forceSwapReclaim() {
	slog.Info("running swapoff -a to force swap reclaim")

	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	if out, err := exec.CommandContext(ctx, "swapoff", "-a").CombinedOutput(); err != nil {
		slog.Warn("swapoff -a failed", "error", err, "output", string(out))
	} else {
		slog.Info("swapoff -a completed")
	}

	if out, err := exec.CommandContext(ctx, "swapon", "-a").CombinedOutput(); err != nil {
		slog.Warn("swapon -a failed", "error", err, "output", string(out))
	} else {
		slog.Info("swapon -a completed, swap re-enabled")
	}
}
