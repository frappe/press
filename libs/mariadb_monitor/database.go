package main

import (
	"database/sql"
	"fmt"
	"net"
	"strconv"
	"strings"
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
}

func NewDatabase(creds MySQLCredentials) *Database {
	db := &Database{creds: creds}
	db.Tcmalloc = &Tcmalloc{db: db}
	return db
}

func NewDatabaseFromMyCnf() (*Database, error) {
	creds, err := LoadMySQLCredentials()
	if err != nil {
		return nil, err
	}
	return NewDatabase(creds), nil
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
	db, err := d.open(opts)
	if err != nil {
		return err
	}
	defer db.Close()

	rows, err := db.Query(query, args...)
	if err != nil {
		return err
	}
	defer rows.Close()

	if err := fn(rows); err != nil {
		return err
	}
	return rows.Err()
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
	db, err := d.open(opts)
	if err != nil {
		return err
	}
	defer db.Close()

	_, err = db.Exec(query)
	return err
}

// open builds a mysql connection from credentials and options.
func (d *Database) open(opts QueryOptions) (*sql.DB, error) {
	timeout := opts.Timeout
	if timeout <= 0 {
		timeout = defaultQueryTimeout
	}

	transport := opts.Transport
	if transport == "" {
		if d.creds.Socket != "" {
			transport = "unix"
		} else {
			transport = "tcp"
		}
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
	db.SetMaxOpenConns(1)
	db.SetConnMaxLifetime(timeout)
	return db, nil
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
