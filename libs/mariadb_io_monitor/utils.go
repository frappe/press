package main

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"

	"os/exec"

	"github.com/cilium/ebpf/perf"
)

// CircularBuffer to keep fixed-size samples

type CircularBuffer[T any] struct {
	mu   sync.RWMutex
	data []T
	head int
	full bool
	size int
}

func NewCircularBuffer[T any](size int) *CircularBuffer[T] {
	return &CircularBuffer[T]{
		data: make([]T, size),
		size: size,
	}
}

func (c *CircularBuffer[T]) Add(s T) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.data[c.head] = s
	c.head = (c.head + 1) % c.size
	if c.head == 0 {
		c.full = true
	}
}

func (c *CircularBuffer[T]) GetLatest() *T {
	c.mu.RLock()
	defer c.mu.RUnlock()

	if len(c.data) == 0 {
		return nil
	}

	// Get most recent item (just before head)
	idx := c.head - 1
	if idx < 0 {
		idx = len(c.data) - 1
	}
	return &c.data[idx]
}

func (c *CircularBuffer[T]) Snapshot() []T {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if !c.full && c.head == 0 {
		return nil
	}
	var out []T
	if c.full {
		out = append(out, c.data[c.head:]...)
		out = append(out, c.data[:c.head]...)
	} else {
		out = append(out, c.data[:c.head]...)
	}
	return out
}

// Helper methods

func isPerfClosedError(err error) bool {
	if err == nil {
		return false
	}
	if err == perf.ErrClosed {
		return true
	}
	e := strings.ToLower(err.Error())
	if (strings.Contains(e, "perf reader closed") ||
		strings.Contains(e, "reader is closed") ||
		strings.Contains(e, "closed") && strings.Contains(e, "perf")) ||
		strings.Contains(strings.ToLower(err.Error()), "file already closed") {
		return true
	}
	return false
}

// func cStr(b []byte) string {
// 	if i := bytes.IndexByte(b, 0); i >= 0 {
// 		return string(b[:i])
// 	}
// 	return string(b)
// }

func captureMariaDBProcessList() (string, error) {
	// max 10s timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "mariadb", "-e", "SHOW FULL PROCESSLIST\\G")
	output, err := cmd.CombinedOutput()
	if ctx.Err() == context.DeadlineExceeded {
		return "", errors.New("mariadb process list command timed out")
	}

	if err != nil {
		return "", fmt.Errorf("error executing mariadb command: %v, output: %s", err, string(output))
	}

	return string(output), nil
}
