package main

import (
	"context"
	"log/slog"
	"os/exec"
	"time"
)

// swapReclaimTimeout is the hard cap on how long we let swapoff/swapon run.
// On a healthy system with plenty of free RAM the kernel will finish in a
// second or two; if it takes longer than this something is wrong then stop
const swapReclaimTimeout = 30 * time.Second

// tryRelieveMemoryPressure performs soft, non-restart memory recovery:
//
//  1. ask tcmalloc to release free pages back to the OS,
//  2. shrink the InnoDB buffer pool when free RAM is below the target,
//  3. force swap reclaim, but only when the system clearly has the headroom
//     to absorb it without falling over.
//
// Returns true if any stage took action and the original InnoDB buffer pool
// size if it was reduced (0 otherwise).
func tryRelieveMemoryPressure(cfg Config, creds MySQLCredentials) (bool, uint64) {
	slog.Info("attempting soft memory pressure relief")
	relieved := false
	var originalBufferSize uint64

	db := NewDatabase(creds)

	if releaseTcmalloc(cfg, db) {
		relieved = true
	}

	mem, memErr := checkMemory()
	if memErr != nil {
		slog.Warn("memory release: failed to read /proc/meminfo", "error", memErr)
	} else {
		if origSize, did := shrinkInnoDBBuffer(cfg, db, mem); did {
			originalBufferSize = origSize
			relieved = true
		}
	}

	// Re-read memory after the previous stages may have freed RAM, then
	// consider forcing swap reclaim.
	if mem2, err := checkMemory(); err == nil {
		if reclaimSwapIfSafe(cfg, mem2) {
			relieved = true
		}
	}

	if relieved {
		slog.Info("soft memory pressure relief completed")
	} else {
		slog.Info("soft memory pressure relief: no actions were necessary")
	}

	return relieved, originalBufferSize
}

// releaseTcmalloc asks the tcmalloc UDF to return free pages to the OS.
func releaseTcmalloc(cfg Config, db *Database) bool {
	ok, err := db.Tcmalloc.IsAvailable()
	if err != nil || !ok {
		return false
	}
	stats, err := db.Tcmalloc.Stats()
	if err != nil {
		slog.Warn("failed to read tcmalloc stats", "error", err)
		return false
	}
	freeInTcmalloc := stats.HeapSize - stats.AllocatedBytes
	thresholdBytes := cfg.Release.TcmallocThresholdMB * 1024 * 1024
	if freeInTcmalloc <= thresholdBytes {
		slog.Debug("tcmalloc free memory below threshold, skipping release",
			"free_mb", freeInTcmalloc/1024/1024,
			"threshold_mb", cfg.Release.TcmallocThresholdMB,
		)
		return false
	}
	released, err := db.Tcmalloc.ReleaseMemory()
	if err != nil {
		slog.Warn("tcmalloc release failed", "error", err)
		return false
	}
	slog.Info("tcmalloc released memory to OS",
		"released_bytes", released,
		"was_free_bytes", freeInTcmalloc,
	)
	return true
}

// shrinkInnoDBBuffer reduces innodb_buffer_pool_size when free RAM is below
// the configured target. Returns the previous size (so the caller can restore
// it later) and whether anything was changed.
func shrinkInnoDBBuffer(cfg Config, db *Database, mem MemoryStatus) (uint64, bool) {
	availableBytes := mem.MemAvailable * 1024
	minFreeBytes := cfg.Release.MinFreeMB * 1024 * 1024

	if availableBytes >= minFreeBytes {
		slog.Debug("memory release: sufficient free memory, skipping buffer reduction",
			"available_mb", mem.MemAvailable/1024,
			"target_free_mb", cfg.Release.MinFreeMB,
		)
		return 0, false
	}

	deficit := minFreeBytes - availableBytes
	slog.Info("insufficient free memory, reducing InnoDB buffer pool",
		"available_mb", mem.MemAvailable/1024,
		"target_free_mb", cfg.Release.MinFreeMB,
		"deficit_mb", deficit/1024/1024,
	)

	bpCfg, err := db.GetInnoDBBufferPoolConfig()
	if err != nil {
		slog.Warn("memory release: failed to get buffer pool config", "error", err)
		return 0, false
	}

	minBufBytes := cfg.Release.InnoDBBufferMinMB * 1024 * 1024
	currentSize := bpCfg.Size
	headroom := minFreeBytes / 4 // avoid re-entering the deficit immediately

	var targetSize uint64
	if deficit+headroom >= currentSize {
		targetSize = minBufBytes
	} else {
		targetSize = currentSize - deficit - headroom
		if targetSize < minBufBytes {
			targetSize = minBufBytes
		}
	}

	if targetSize >= currentSize {
		slog.Info("memory release: InnoDB buffer pool already at minimum, cannot reduce further",
			"current_mb", currentSize/1024/1024,
			"min_mb", minBufBytes/1024/1024,
		)
		return 0, false
	}

	actual, err := db.ResizeInnoDBBufferPool(targetSize)
	if err != nil {
		slog.Warn("memory release: buffer pool resize failed",
			"error", err,
			"current_mb", currentSize/1024/1024,
			"target_mb", targetSize/1024/1024,
		)
		return 0, false
	}
	slog.Info("memory release: reduced InnoDB buffer pool",
		"from_mb", currentSize/1024/1024,
		"to_mb", actual/1024/1024,
		"freed_approx_mb", (currentSize-actual)/1024/1024,
	)
	return currentSize, true
}

// reclaimSwapIfSafe runs swapoff -a / swapon -a, but only when every guard
// passes. swapoff under pressure is a known cause of multi-minute kernel
// stalls; the guards below exist to make sure we never trigger one.
func reclaimSwapIfSafe(cfg Config, mem MemoryStatus) bool {
	if cfg.Release.SwapReclaimMinMB == 0 {
		return false // disabled
	}

	cgMem := readCgroupMemory()
	mariadbSwapMB := cgMem.SwapUsage / 1024 / 1024
	if mariadbSwapMB < cfg.Release.SwapReclaimMinMB {
		slog.Debug("swap reclaim: mariadb swap usage below threshold, skipping",
			"mariadb_swap_mb", mariadbSwapMB,
			"threshold_mb", cfg.Release.SwapReclaimMinMB,
		)
		return false
	}

	if mem.SwapTotal == 0 {
		return false
	}
	availableBytes := mem.MemAvailable * 1024
	totalSwapUsedBytes := (mem.SwapTotal - mem.SwapFree) * 1024
	if totalSwapUsedBytes == 0 {
		return false
	}

	ratio := cfg.Release.SwapReclaimFreeRAMRatio
	if ratio <= 0 {
		ratio = 1.5
	}
	requiredFree := uint64(float64(totalSwapUsedBytes) * ratio)
	if availableBytes < requiredFree {
		slog.Info("swap reclaim: not enough free RAM to safely absorb swap, skipping",
			"available_mb", availableBytes/1024/1024,
			"total_swap_used_mb", totalSwapUsedBytes/1024/1024,
			"required_free_mb", requiredFree/1024/1024,
			"ratio", ratio,
		)
		return false
	}

	if psi, err := checkPSI("memory"); err == nil && psi >= cfg.Release.PSIMemoryThreshold {
		slog.Info("swap reclaim: PSI memory above relief threshold, skipping",
			"psi_memory", psi,
			"threshold", cfg.Release.PSIMemoryThreshold,
		)
		return false
	}

	slog.Info("swap reclaim: guards passed, forcing swap reclaim",
		"mariadb_swap_mb", mariadbSwapMB,
		"available_mb", availableBytes/1024/1024,
		"total_swap_used_mb", totalSwapUsedBytes/1024/1024,
	)
	return forceSwapReclaim()
}

// forceSwapReclaim runs swapoff -a then swapon -a with a hard timeout.
// Returns true if either command made progress.
func forceSwapReclaim() bool {
	ok := false

	ctx, cancel := context.WithTimeout(context.Background(), swapReclaimTimeout)
	defer cancel()

	if out, err := exec.CommandContext(ctx, "swapoff", "-a").CombinedOutput(); err != nil {
		slog.Warn("swapoff -a failed", "error", err, "output", string(out))
	} else {
		slog.Info("swapoff -a completed")
		ok = true
	}

	// Re-enable swap even if swapoff failed; swapon -a is idempotent.
	ctx2, cancel2 := context.WithTimeout(context.Background(), swapReclaimTimeout)
	defer cancel2()
	if out, err := exec.CommandContext(ctx2, "swapon", "-a").CombinedOutput(); err != nil {
		slog.Warn("swapon -a failed, swap may now be disabled", "error", err, "output", string(out))
	} else {
		slog.Info("swapon -a completed, swap re-enabled")
	}

	return ok
}
