package main

import (
	"database/sql"
	"errors"
	"fmt"
)

type TcmallocStats struct {
	AllocatedBytes int64
	HeapSize       int64
}

type Tcmalloc struct {
	db *Database
}

var errTcmallocUnavailable = errors.New("tcmalloc UDF is not available")

func (t *Tcmalloc) IsAvailable() (bool, error) {
	var v int64
	err := t.db.Query("SELECT tcmalloc_available()", func(rows *sql.Rows) error {
		if rows.Next() {
			return rows.Scan(&v)
		}
		return nil
	})
	return v == 1, err
}

func (t *Tcmalloc) ensureAvailable() error {
	ok, err := t.IsAvailable()
	if err != nil {
		return err
	}
	if !ok {
		return errTcmallocUnavailable
	}
	return nil
}

func (t *Tcmalloc) Stats() (TcmallocStats, error) {
	if err := t.ensureAvailable(); err != nil {
		return TcmallocStats{}, err
	}

	var s TcmallocStats
	queries := []struct {
		query string
		dest  *int64
	}{
		{"SELECT tcmalloc_allocated_bytes()", &s.AllocatedBytes},
		{"SELECT tcmalloc_heap_size()", &s.HeapSize},
	}
	for _, q := range queries {
		if err := t.db.Query(q.query, func(rows *sql.Rows) error {
			if rows.Next() {
				return rows.Scan(q.dest)
			}
			return nil
		}); err != nil {
			return s, fmt.Errorf("%s: %w", q.query, err)
		}
	}
	return s, nil
}

// ReleaseMemory releases free pages to the OS and returns bytes released.
func (t *Tcmalloc) ReleaseMemory() (int64, error) {
	if err := t.ensureAvailable(); err != nil {
		return 0, err
	}

	var released int64
	err := t.db.Query("SELECT tcmalloc_release_memory()", func(rows *sql.Rows) error {
		if rows.Next() {
			return rows.Scan(&released)
		}
		return nil
	})
	return released, err
}

// FreeBytes returns bytes held free inside tcmalloc (pageheap + caches)
// that have not been returned to the OS and are not in use by the app.
func (t *Tcmalloc) FreeBytes() (int64, error) {
	if err := t.ensureAvailable(); err != nil {
		return 0, err
	}
	var v int64
	err := t.db.Query("SELECT tcmalloc_free_bytes()", func(rows *sql.Rows) error {
		if rows.Next() {
			return rows.Scan(&v)
		}
		return nil
	})
	return v, err
}

// ReleaseBytes asks tcmalloc to return n bytes of free pages to the OS.
// Returns the number of bytes actually decommitted.
func (t *Tcmalloc) ReleaseBytes(n int64) (int64, error) {
	if err := t.ensureAvailable(); err != nil {
		return 0, err
	}
	var released int64
	err := t.db.Query(fmt.Sprintf("SELECT tcmalloc_release_bytes(%d)", n), func(rows *sql.Rows) error {
		if rows.Next() {
			return rows.Scan(&released)
		}
		return nil
	})
	return released, err
}
