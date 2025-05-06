package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/go-mysql-org/go-mysql/replication"
	_ "github.com/marcboeker/go-duckdb/v2"
	"vitess.io/vitess/go/vt/sqlparser"

	"github.com/xitongsys/parquet-go-source/local"
	"github.com/xitongsys/parquet-go/parquet"
	"github.com/xitongsys/parquet-go/source"
	"github.com/xitongsys/parquet-go/writer"
)

const CREATE_TABLE_SQL string = `
CREATE TABLE IF NOT EXISTS query (
	binlog VARCHAR,
	db_name VARCHAR,
	table_name VARCHAR,
	timestamp INTEGER,
	type VARCHAR,
	row_id INTEGER,
	event_size INTEGER
)
`

const INSERT_QUERY_SQL string = "INSERT INTO query (binlog, db_name, table_name, timestamp, type, row_id, event_size) VALUES %s"

type Query struct {
	Timestamp uint32
	Metadata  SQLSourceMetadata
	RowId     int32
	EventSize uint32
	SQL       string
}

type BinlogIndexer struct {
	BatchSize  int
	binlogName string
	binlogPath string

	// State
	queries      []Query
	currentRowId int32

	// Internal
	db        *sql.DB
	fw        source.ParquetFile
	pw        *writer.ParquetWriter
	parser    *replication.BinlogParser
	sqlParser *sqlparser.Parser
	isClosed  bool

	// AnnotateRowsEvent parsing related
	annotateRowsEvent          *replication.MariadbAnnotateRowsEvent
	annotateRowsEventTimestamp uint32
	tableMapEvents             [][]string // list of [database, table]
	annotateRowsEventSize      uint32     // actual event + related events (table map + write rows)
}

type ParquetRow struct {
	Id    int32  `parquet:"name=id, type=INT32"`
	Query string `parquet:"name=query, type=BYTE_ARRAY, convertedtype=UTF8, encoding=PLAIN_DICTIONARY"`
}

//export NewBinlogIndexer
func NewBinlogIndexer(basePath string, binlogPath string, databaseFilename string, batchSize int) (*BinlogIndexer, error) {
	if _, err := os.Stat(basePath); os.IsNotExist(err) {
		return nil, fmt.Errorf("base path does not exist: %w", err)
	}
	binlogFilename := filepath.Base(binlogPath)
	db, err := sql.Open("duckdb", filepath.Join(basePath, databaseFilename))
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	// Create SQL sql_parser
	sql_parser, err := sqlparser.New(sqlparser.Options{})
	if err != nil {
		return nil, fmt.Errorf("failed to create sql parser: %w", err)
	}

	// Create table
	_, err = db.Exec(CREATE_TABLE_SQL)
	if err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("failed to create table: %w", err)
	}

	/*
	 * Delete current binlog data (if exists)
	 * Because, parquet file doesn't support appending data
	 * So we need to delete the current binlog data before we start index it again
	 */

	_, err = db.Exec("DELETE FROM query WHERE binlog = ?", binlogFilename)
	if err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("failed to delete binlog data: %w", err)
	}

	parquet_filepath := filepath.Join(basePath, fmt.Sprintf("queries_%s.parquet", binlogFilename))
	_ = os.Remove(parquet_filepath)

	// Estimate out row group size
	pageSize, err := EstimateParquetPageSize(binlogPath)
	if err != nil {
		return nil, fmt.Errorf("failed to estimate row group size: %w", err)
	}
	// Create parquet writer
	fw, err := local.NewLocalFileWriter(parquet_filepath)
	if err != nil {
		return nil, fmt.Errorf("failed to create local file: %w", err)
	}

	parquetWriter, err := writer.NewParquetWriter(fw, new(ParquetRow), 1)
	parquetWriter.RowGroupSize = 128 * 1024 * 1024 // 128MB

	parquetWriter.PageSize = pageSize
	parquetWriter.CompressionType = parquet.CompressionCodec_ZSTD

	return &BinlogIndexer{
		BatchSize:      batchSize,
		binlogName:     binlogFilename,
		binlogPath:     binlogPath,
		queries:        make([]Query, 0),
		currentRowId:   1,
		db:             db,
		fw:             fw,
		pw:             parquetWriter,
		parser:         replication.NewBinlogParser(),
		sqlParser:      sql_parser,
		isClosed:       false,
		tableMapEvents: make([][]string, 0),
	}, nil
}

func (p *BinlogIndexer) Start() error {
	err := p.parser.ParseFile(p.binlogPath, 0, p.onBinlogEvent)
	if err != nil {
		return fmt.Errorf("failed to parse binlog: %w", err)
	}
	// Check for any pending annotate rows event
	p.commitAnnotateRowsEvent()
	// Flush the last batch
	err = p.flush()
	if err != nil {
		return fmt.Errorf("failed to flush: %w", err)
	}
	// Close everything
	p.Close()
	return nil
}

func (p *BinlogIndexer) onBinlogEvent(e *replication.BinlogEvent) error {
	commitAnnotateRowsEvent := false
	switch e.Header.EventType {
	case replication.MARIADB_ANNOTATE_ROWS_EVENT:
		if event, ok := e.Event.(*replication.MariadbAnnotateRowsEvent); ok {
			p.annotateRowsEvent = event
			p.annotateRowsEventSize = e.Header.EventSize
			p.annotateRowsEventTimestamp = e.Header.Timestamp
		}
	case replication.TABLE_MAP_EVENT:
		if event, ok := e.Event.(*replication.TableMapEvent); ok {
			p.tableMapEvents = append(p.tableMapEvents, []string{string(event.Schema), string(event.Table)})
			p.annotateRowsEventSize += e.Header.EventSize
		}
	case replication.WRITE_ROWS_EVENTv1, replication.UPDATE_ROWS_EVENTv1, replication.DELETE_ROWS_EVENTv1:
		if _, ok := e.Event.(*replication.RowsEvent); ok {
			p.annotateRowsEventSize += e.Header.EventSize
		}
	case replication.QUERY_EVENT:
		if event, ok := e.Event.(*replication.QueryEvent); ok {
			p.addQuery(string(event.Query), string(event.Schema), e.Header.Timestamp, e.Header.EventSize)
		}
		commitAnnotateRowsEvent = true
	default:
		commitAnnotateRowsEvent = true
	}

	if commitAnnotateRowsEvent {
		p.commitAnnotateRowsEvent()
	}

	return nil
}

func (p *BinlogIndexer) commitAnnotateRowsEvent() {
	if p.annotateRowsEvent == nil {
		return
	}

	if len(p.tableMapEvents) == 0 {
		return
	}

	metadata := ExtractSQLMetadata(string(p.annotateRowsEvent.Query), p.sqlParser, "")
	metadata.Tables = make([]*SQLTable, 0)
	for _, table := range p.tableMapEvents {
		metadata.Tables = append(metadata.Tables, &SQLTable{
			Database: table[0],
			Table:    table[1],
		})
	}

	p.queries = append(p.queries, Query{
		Timestamp: p.annotateRowsEventTimestamp,
		Metadata:  metadata,
		RowId:     p.currentRowId,
		EventSize: p.annotateRowsEventSize,
		SQL:       string(p.annotateRowsEvent.Query),
	})
	p.currentRowId += 1

	// reset
	p.annotateRowsEvent = nil
	p.annotateRowsEventSize = 0
	p.annotateRowsEventTimestamp = 0
	p.tableMapEvents = make([][]string, 0)

	p.flushIfNeeded()
}

func (p *BinlogIndexer) addQuery(query string, schema string, timestamp uint32, eventSize uint32) {
	metadata := ExtractSQLMetadata(query, p.sqlParser, string(schema))

	p.queries = append(p.queries, Query{
		Timestamp: timestamp,
		Metadata:  metadata,
		RowId:     p.currentRowId,
		EventSize: eventSize,
		SQL:       query,
	})
	p.currentRowId += 1
	p.flushIfNeeded()
}

func (p *BinlogIndexer) flushIfNeeded() {
	if len(p.queries) >= p.BatchSize {
		err := p.flush()
		if err != nil {
			fmt.Printf("[WARN] failed to flush: %v\n", err)
		}
	}
}

func (p *BinlogIndexer) flush() error {
	if len(p.queries) == 0 {
		return nil
	}
	// Create transaction
	tx, err := p.db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin db transaction: %w", err)
	}

	defer func() {
		// In case of error rollback changes
		_ = tx.Rollback()
	}()

	// Write the queries to db
	batch := make([]string, 0, len(p.queries))
	for _, query := range p.queries {
		for _, table := range query.Metadata.Tables {
			batch = append(batch, fmt.Sprintf("('%s', '%s', '%s', %d, '%s', %d, %d)",
				p.binlogName, table.Database, table.Table, query.Timestamp, query.Metadata.Type, query.RowId, query.EventSize))
		}
	}

	// Insert the queries
	_, err = tx.Exec(fmt.Sprintf(INSERT_QUERY_SQL, strings.Join(batch, ",")))
	if err != nil {
		return fmt.Errorf("failed to insert queries: %w", err)
	}

	// Release memory of batch
	batch = nil

	// Insert all query in parquet file
	for _, query := range p.queries {
		if err = p.pw.Write(ParquetRow{
			Id:    query.RowId,
			Query: query.SQL,
		}); err != nil {
			return fmt.Errorf("failed to write query to parquet file: %w", err)
		}
	}

	// Commit the transaction
	err = tx.Commit()
	if err != nil {
		return fmt.Errorf("failed to commit db transaction: %w", err)
	}

	// Clear the queries
	p.queries = make([]Query, 0)

	return nil
}

func (p *BinlogIndexer) Close() {
	if p.isClosed {
		return
	}
	// Do a final flush
	if err := p.flush(); err != nil {
		fmt.Printf("[WARN] failed to flush: %v\n", err)
	}
	// try to stop the parquet writer
	if err := p.pw.WriteStop(); err != nil {
		fmt.Printf("[WARN] failed to stop parquet writer: %v\n", err)
	}

	// try to close the parquet file
	if err := p.fw.Close(); err != nil {
		fmt.Printf("[WARN] failed to close parquet file: %v\n", err)
	}
	// try to close the db
	if err := p.db.Close(); err != nil {
		fmt.Printf("[WARN] failed to close db: %v\n", err)
	}

	p.isClosed = true
}

//export RemoveBinlogIndex
func RemoveBinlogIndex(basePath string, binlogPath string, databaseFilename string) error {
	binlogFilename := filepath.Base(binlogPath)

	db, err := sql.Open("duckdb", filepath.Join(basePath, databaseFilename))
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}

	defer func() {
		_ = db.Close()
	}()

	// drop binlog
	_, err = db.Exec("DELETE FROM query WHERE binlog = ?", binlogFilename)
	if err != nil {
		return fmt.Errorf("failed to delete binlog data: %w", err)
	}

	// drop parquet file
	parquetFilepath := filepath.Join(basePath, fmt.Sprintf("queries_%s.parquet", binlogFilename))
	_ = os.Remove(parquetFilepath)
	return nil
}
