package main

import (
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
)

// IORateLimiter is a leaky bucket rate limiter for IO operations
type IORateLimiter struct {
	mu         sync.Mutex
	tokens     float64
	maxTokens  float64
	lastTime   time.Time
	refillRate float64 // tokens per nanosecond
}

func NewIORateLimiter(maxOpsPerSecond float64) *IORateLimiter {
	return &IORateLimiter{
		tokens:     maxOpsPerSecond,
		maxTokens:  maxOpsPerSecond,
		lastTime:   time.Now(),
		refillRate: maxOpsPerSecond / float64(time.Second),
	}
}

// Wait blocks until an IO operation is allowed
func (r *IORateLimiter) Wait() {
	r.mu.Lock()
	defer r.mu.Unlock()

	now := time.Now()
	elapsed := now.Sub(r.lastTime)
	r.lastTime = now

	// refill tokens based on elapsed time
	r.tokens += float64(elapsed) * r.refillRate
	if r.tokens > r.maxTokens {
		r.tokens = r.maxTokens
	}

	// if we have a token, consume it
	if r.tokens >= 1.0 {
		r.tokens -= 1.0
		return
	}

	// wait until we have 1 token
	tokensNeeded := 1.0 - r.tokens
	waitDuration := time.Duration(tokensNeeded / r.refillRate)

	r.mu.Unlock()
	time.Sleep(waitDuration)
	r.mu.Lock()

	r.lastTime = time.Now()
	r.tokens = 0
}

// CheckLowIOOrPause checks if the system IO wait is below the threshold.
// If it is above, it calls closeFd, waits up to 1 minute for it to drop,
// checks periodically, and calls openFd when it drops.
// If it remains high after 1 minute, it returns an error.
func CheckLowIOOrPause(thresholdPercent float64, closeFd func(), openFd func() error) error {
	wait, err := getIOWait()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Warning: failed to monitor IO: %v\n", err)
		return nil
	}

	if wait <= thresholdPercent {
		return nil
	}

	// High IO detected
	fmt.Printf("High IO detected (%.2f%% > %.2f%%). Pausing execution...\n", wait, thresholdPercent)
	if closeFd != nil {
		closeFd()
	}

	// Wait loop (max 1 minute)
	timeout := time.After(1 * time.Minute)
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeout:
			return fmt.Errorf("IO wait remained high (%.2f%%) for over 1 minute. Exiting to avoid IO freeze", wait)
		case <-ticker.C:
			wait, err := getIOWait()
			if err != nil {
				fmt.Fprintf(os.Stderr, "Warning: failed to monitor IO during pause: %v\n", err)
				continue
			}
			if wait <= thresholdPercent {
				fmt.Printf("IO wait dropped to %.2f%%. Resuming...\n", wait)
				if openFd != nil {
					if err := openFd(); err != nil {
						return fmt.Errorf("failed to reopen file: %v", err)
					}
				}
				return nil
			}
			fmt.Printf("IO wait still high (%.2f%%)... waiting\n", wait)
		}
	}
}

func getIOWait() (float64, error) {
	// Sample 1
	t1, err := cpu.Times(false) // returns total cpu times
	if err != nil {
		return 0, err
	}
	if len(t1) == 0 {
		return 0, fmt.Errorf("no cpu stats found")
	}

	time.Sleep(100 * time.Millisecond) // Short sample duration

	// Sample 2
	t2, err := cpu.Times(false)
	if err != nil {
		return 0, err
	}
	if len(t2) == 0 {
		return 0, fmt.Errorf("no cpu stats found")
	}

	// Calculate delta
	total1 := t1[0].User + t1[0].System + t1[0].Idle + t1[0].Nice + t1[0].Iowait + t1[0].Irq + t1[0].Softirq + t1[0].Steal + t1[0].Guest + t1[0].GuestNice
	total2 := t2[0].User + t2[0].System + t2[0].Idle + t2[0].Nice + t2[0].Iowait + t2[0].Irq + t2[0].Softirq + t2[0].Steal + t2[0].Guest + t2[0].GuestNice

	deltaTotal := total2 - total1
	deltaIOWait := t2[0].Iowait - t1[0].Iowait

	if deltaTotal == 0 {
		return 0, nil
	}

	return (deltaIOWait / deltaTotal) * 100.0, nil
}
