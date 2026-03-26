package main

import (
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

const (
	logDir     = "/var/log/mariadb-monitor"
	logFile    = logDir + "/monitor.log"
	maxLogSize = 50 * 1024 * 1024 // 50 MB
)

type truncatingWriter struct {
	mu      sync.Mutex
	f       *os.File
	written int64
	maxSize int64
}

func newTruncatingWriter(path string, maxSize int64) (*truncatingWriter, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return nil, err
	}

	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return nil, err
	}

	info, err := f.Stat()
	if err != nil {
		f.Close()
		return nil, err
	}

	return &truncatingWriter{
		f:       f,
		written: info.Size(),
		maxSize: maxSize,
	}, nil
}

func (w *truncatingWriter) Write(p []byte) (n int, err error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	if w.written+int64(len(p)) > w.maxSize {
		if err := w.f.Truncate(0); err != nil {
			return 0, err
		}
		if _, err := w.f.Seek(0, io.SeekStart); err != nil {
			return 0, err
		}
		w.written = 0
	}

	n, err = w.f.Write(p)
	w.written += int64(n)
	return n, err
}

func (w *truncatingWriter) Close() error {
	return w.f.Close()
}

func setupLogging(logLevel string) (*truncatingWriter, error) {
	writer, err := newTruncatingWriter(logFile, maxLogSize)
	if err != nil {
		return nil, err
	}

	level := slog.LevelWarn

	switch strings.ToUpper(logLevel) {
	case "DEBUG":
		level = slog.LevelDebug
	case "INFO":
		level = slog.LevelInfo
	case "WARN", "WARNING":
		level = slog.LevelWarn
	case "ERROR":
		level = slog.LevelError
	}

	multiWriter := io.MultiWriter(writer, os.Stderr)

	logger := slog.New(slog.NewJSONHandler(multiWriter, &slog.HandlerOptions{
		Level: level,
	}))
	slog.SetDefault(logger)

	return writer, nil
}
