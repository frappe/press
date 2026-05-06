package main

import (
	"database/sql"
	"fmt"
	"net"
	"strconv"
	"time"

	"github.com/go-sql-driver/mysql"
)

const defaultQueryTimeout = 5 * time.Second

type QueryOptions struct {
	Timeout   time.Duration
	Transport string
}

type Database struct {
	creds MySQLCredentials
}

func NewDatabase(creds MySQLCredentials) *Database {
	return &Database{creds: creds}
}

func NewDatabaseFromMyCnf() (*Database, error) {
	creds, err := LoadMySQLCredentials()
	if err != nil {
		return nil, err
	}
	return &Database{creds: creds}, nil
}

func (d *Database) QueryWithOptions(opts QueryOptions, query string, fn func(*sql.Rows) error) error {
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
			return fmt.Errorf("unix socket transport requested but socket path is not configured")
		}
		cfg.Net = "unix"
		cfg.Addr = d.creds.Socket
	case "tcp":
		if d.creds.Host == "" || d.creds.Port == 0 {
			return fmt.Errorf("tcp transport requested but host/port are not configured")
		}
		cfg.Net = "tcp"
		cfg.Addr = net.JoinHostPort(d.creds.Host, strconv.Itoa(d.creds.Port))
	default:
		return fmt.Errorf("unknown transport %q: must be \"unix\" or \"tcp\"", transport)
	}

	db, err := sql.Open("mysql", cfg.FormatDSN())
	if err != nil {
		return err
	}
	defer db.Close()
	db.SetMaxOpenConns(1)
	db.SetConnMaxLifetime(timeout)

	rows, err := db.Query(query)
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
