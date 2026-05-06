package main

import (
	"database/sql"
	"errors"
	"fmt"
)

type TcmallocStats struct {
	AllocatedBytes int64
	HeapSize       int64
	FreeBytes      int64
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
		{"SELECT tcmalloc_free_bytes()", &s.FreeBytes},
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

// Property reads a single numeric tcmalloc property by name.
// Returns 0, false if the property is unknown.
func (t *Tcmalloc) Property(name string) (int64, bool, error) {
	if err := t.ensureAvailable(); err != nil {
		return 0, false, err
	}

	var val sql.NullInt64
	err := t.db.QueryWithArgs("SELECT tcmalloc_property(?)", []any{name}, func(rows *sql.Rows) error {
		if rows.Next() {
			return rows.Scan(&val)
		}
		return nil
	})
	if err != nil {
		return 0, false, err
	}
	return val.Int64, val.Valid, nil
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

func (t *Tcmalloc) StatsText() (string, error) {
	if err := t.ensureAvailable(); err != nil {
		return "", err
	}

	var text string
	err := t.db.Query("SELECT tcmalloc_stats()", func(rows *sql.Rows) error {
		if rows.Next() {
			return rows.Scan(&text)
		}
		return nil
	})
	return text, err
}
