package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/go-sql-driver/mysql"
)

const defaultQueryTimeout = 5 * time.Second

type QueryOptions struct {
	Timeout   time.Duration
	Transport string
}

type Database struct {
	creds    MySQLCredentials
	Tcmalloc *Tcmalloc

	mu    sync.Mutex
	pools map[string]*sql.DB // keyed by transport
}

func NewDatabase(creds MySQLCredentials) *Database {
	d := &Database{creds: creds, pools: map[string]*sql.DB{}}
	d.Tcmalloc = &Tcmalloc{db: d}
	return d
}

func NewDatabaseFromMyCnf() (*Database, error) {
	creds, err := LoadMySQLCredentials()
	if err != nil {
		return nil, err
	}
	return NewDatabase(creds), nil
}

// Close releases any cached pools. Safe to call multiple times.
func (d *Database) Close() {
	d.mu.Lock()
	defer d.mu.Unlock()
	for k, p := range d.pools {
		_ = p.Close()
		delete(d.pools, k)
	}
}

func (d *Database) QueryWithOptions(opts QueryOptions, query string, fn func(*sql.Rows) error) error {
	return d.queryWithOptionsAndArgs(opts, query, nil, fn)
}

func (d *Database) QueryWithArgs(query string, args []any, fn func(*sql.Rows) error) error {
	return d.queryWithOptionsAndArgs(QueryOptions{}, query, args, fn)
}

func (d *Database) QueryWithOptionsAndArgs(opts QueryOptions, query string, args []any, fn func(*sql.Rows) error) error {
	return d.queryWithOptionsAndArgs(opts, query, args, fn)
}

func (d *Database) queryWithOptionsAndArgs(opts QueryOptions, query string, args []any, fn func(*sql.Rows) error) error {
	transport := d.resolveTransport(opts.Transport)
	timeout := opts.Timeout
	if timeout <= 0 {
		timeout = defaultQueryTimeout
	}

	return d.withRetry(transport, timeout, func(db *sql.DB) error {
		ctx, cancel := context.WithTimeout(context.Background(), timeout)
		defer cancel()

		rows, err := db.QueryContext(ctx, query, args...)
		if err != nil {
			return err
		}
		defer rows.Close()

		if err := fn(rows); err != nil {
			return err
		}
		return rows.Err()
	})
}

func (d *Database) Query(query string, fn func(*sql.Rows) error) error {
	return d.QueryWithOptions(QueryOptions{}, query, fn)
}

func (d *Database) QueryTCP(query string, fn func(*sql.Rows) error) error {
	return d.QueryWithOptions(QueryOptions{Transport: "tcp"}, query, fn)
}

func (d *Database) QuerySocket(query string, fn func(*sql.Rows) error) error {
	return d.QueryWithOptions(QueryOptions{Transport: "unix"}, query, fn)
}

func (d *Database) execSocket(query string) error {
	return d.execWithOptions(QueryOptions{Transport: "unix"}, query)
}

func (d *Database) execWithOptions(opts QueryOptions, query string) error {
	transport := d.resolveTransport(opts.Transport)
	timeout := opts.Timeout
	if timeout <= 0 {
		timeout = defaultQueryTimeout
	}

	return d.withRetry(transport, timeout, func(db *sql.DB) error {
		ctx, cancel := context.WithTimeout(context.Background(), timeout)
		defer cancel()
		_, err := db.ExecContext(ctx, query)
		return err
	})
}

// withRetry runs fn against the cached pool for transport. On a connection-
// level failure (timeout, broken pipe, server gone) it discards the cached
// pool and retries up to 5 times with a fresh one. Any further failure is returned.
func (d *Database) withRetry(transport string, timeout time.Duration, fn func(*sql.DB) error) error {
	for attempt := 0; attempt < 5; attempt++ {
		db, err := d.pool(transport, timeout)
		if err != nil {
			return err
		}
		err = fn(db)
		if err == nil {
			return nil
		}
		if attempt == 0 && isRetryableConnError(err) {
			d.dropPool(transport)
			continue
		}
		return err
	}
	return nil
}

func (d *Database) resolveTransport(t string) string {
	if t != "" {
		return t
	}
	if d.creds.Socket != "" {
		return "unix"
	}
	return "tcp"
}

func (d *Database) pool(transport string, timeout time.Duration) (*sql.DB, error) {
	d.mu.Lock()
	defer d.mu.Unlock()

	if p, ok := d.pools[transport]; ok {
		return p, nil
	}

	cfg := mysql.NewConfig()
	cfg.User = d.creds.User
	cfg.Passwd = d.creds.Password // pragma: allowlist secret
	cfg.Timeout = timeout
	cfg.ReadTimeout = timeout
	cfg.WriteTimeout = timeout

	switch transport {
	case "unix":
		if d.creds.Socket == "" {
			return nil, fmt.Errorf("unix socket transport requested but socket path is not configured")
		}
		cfg.Net = "unix"
		cfg.Addr = d.creds.Socket
	case "tcp":
		if d.creds.Host == "" || d.creds.Port == 0 {
			return nil, fmt.Errorf("tcp transport requested but host/port are not configured")
		}
		cfg.Net = "tcp"
		cfg.Addr = net.JoinHostPort(d.creds.Host, strconv.Itoa(d.creds.Port))
	default:
		return nil, fmt.Errorf("unknown transport %q: must be \"unix\" or \"tcp\"", transport)
	}

	db, err := sql.Open("mysql", cfg.FormatDSN())
	if err != nil {
		return nil, err
	}
	// One connection is plenty for a monitor and keeps the footprint small.
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	db.SetConnMaxLifetime(5 * time.Minute)
	db.SetConnMaxIdleTime(2 * time.Minute)

	d.pools[transport] = db
	return db, nil
}

func (d *Database) dropPool(transport string) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if p, ok := d.pools[transport]; ok {
		_ = p.Close()
		delete(d.pools, transport)
	}
}

// isRetryableConnError reports whether err looks like a connection-level
// failure where a fresh connection might succeed.
func isRetryableConnError(err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, mysql.ErrInvalidConn) || errors.Is(err, sql.ErrConnDone) {
		return true
	}
	if errors.Is(err, context.DeadlineExceeded) {
		return true
	}
	var netErr net.Error
	if errors.As(err, &netErr) && netErr.Timeout() {
		return true
	}
	msg := err.Error()
	switch {
	case strings.Contains(msg, "broken pipe"),
		strings.Contains(msg, "connection reset"),
		strings.Contains(msg, "EOF"),
		strings.Contains(msg, "bad connection"),
		strings.Contains(msg, "server has gone away"):
		return true
	}
	return false
}

// queryKVStr executes a two-column (name, value) query and returns a map of
// lowercase name -> string.
func (d *Database) queryKVStr(query string) (map[string]string, error) {
	result := make(map[string]string)
	err := d.Query(query, func(rows *sql.Rows) error {
		for rows.Next() {
			var name, val string
			if err := rows.Scan(&name, &val); err != nil {
				return err
			}
			result[strings.ToLower(name)] = val
		}
		return nil
	})
	return result, err
}

// queryKVUint64 executes a two-column (name, value) query and returns a map of
// lowercase name -> uint64. Non-numeric values are skipped.
func (d *Database) queryKVUint64(query string) (map[string]uint64, error) {
	result := make(map[string]uint64)
	err := d.Query(query, func(rows *sql.Rows) error {
		for rows.Next() {
			var name, val string
			if err := rows.Scan(&name, &val); err != nil {
				return err
			}
			if n, err := strconv.ParseUint(val, 10, 64); err == nil {
				result[strings.ToLower(name)] = n
			}
		}
		return nil
	})
	return result, err
}
