package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"

	"github.com/go-mysql-org/go-mysql/replication"
	_ "github.com/marcboeker/go-duckdb/v2"
	"github.com/parquet-go/parquet-go"
	"github.com/parquet-go/parquet-go/compress/snappy"
	"github.com/parquet-go/parquet-go/compress/zstd"

	"vitess.io/vitess/go/vt/sqlparser"
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

const INSERT_QUERY_SQL string = "INSERT INTO query (binlog, db_name, table_name, timestamp, type, row_id, event_size) VALUES "

type Query struct {
	Timestamp uint32
	Metadata  SQLSourceMetadata
	RowId     int32
	EventSize uint32
	SQL       string
}

type BinlogIndexer struct {
	BatchSize       int
	binlogName      string
	binlogPath      string
	compressionMode string // "low-memory" or "balanced"

	// State
	queries         []Query
	currentRowId    int32
	estimatedMemory int64 // Track estimated memory usage in bytes

	// Internal
	db                       *sql.DB
	fw                       *os.File
	pw                       *parquet.GenericWriter[ParquetRow]
	parquetBuffer            []ParquetRow
	parser                   *replication.BinlogParser
	sqlParser                *sqlparser.Parser
	isClosed                 bool
	sqlStringBuilderForFlush strings.Builder

	// String interning for memory optimization
	stringCache map[string]string

	// AnnotateRowsEvent parsing related
	annotateRowsEvent          *replication.MariadbAnnotateRowsEvent
	annotateRowsEventTimestamp uint32
	tableMapEvents             [][]string // list of [database, table]
	annotateRowsEventSize      uint32     // actual event + related events (table map + write rows)
}

type ParquetRow struct {
	Id    int32  `parquet:"id, type=INT32"`
	Query string `parquet:"query, type=BYTE_ARRAY, convertedtype=UTF8, encoding=PLAIN"`
}

//export NewBinlogIndexer
func NewBinlogIndexer(basePath string, binlogPath string, databaseFilename string, compressionMode string) (*BinlogIndexer, error) {
	if _, err := os.Stat(basePath); os.IsNotExist(err) {
		return nil, fmt.Errorf("base path does not exist: %w", err)
	}
	binlogFilename := filepath.Base(binlogPath)

	// Configure DuckDB memory based on compression mode
	var duckdbMemoryLimit string
	switch compressionMode {
	case "low-memory":
		duckdbMemoryLimit = "15MB" // Aggressive limit for <50MB target
	case "high-compression":
		duckdbMemoryLimit = "512MB" // Large memory allowance for 1GB target
	default: // "balanced"
		duckdbMemoryLimit = "50MB" // Moderate limit
	}

	dbPath := filepath.Join(basePath, databaseFilename) + "?memory_limit=" + duckdbMemoryLimit + "&threads=1"
	db, err := sql.Open("duckdb", dbPath)
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

	// Create file writer
	parquetFile, err := os.Create(parquet_filepath)
	if err != nil {
		return nil, fmt.Errorf("failed to create parquet file: %w", err)
	}
	var parquetOptions []parquet.WriterOption

	switch compressionMode {
	case "low-memory":
		// Snappy: ~5MB compression buffer, minimal page buffers
		parquetOptions = []parquet.WriterOption{
			parquet.Compression(&snappy.Codec{}),
			parquet.PageBufferSize(512 * 1024), // 512KB
			parquet.MaxRowsPerRowGroup(100),    // Flush every 100 rows
			parquet.DataPageStatistics(false),
		}
	case "high-compression":
		// ZSTD max compression: Large buffers for maximum compression ratio
		parquetOptions = []parquet.WriterOption{
			parquet.Compression(&zstd.Codec{Level: zstd.SpeedBestCompression}),
			parquet.PageBufferSize(64 * 1024 * 1024), // 64MB page buffer
			parquet.MaxRowsPerRowGroup(50000),        // Very large row groups
			parquet.DataPageStatistics(true),         // Enable statistics for better compression
			parquet.ColumnPageBuffers(
				parquet.NewFileBufferPool(basePath, "tmp_buffers.*"), // File-backed buffers
			),
		}
	default: // "balanced" mode
		// ZSTD default: Good compression, moderate buffers
		parquetOptions = []parquet.WriterOption{
			parquet.Compression(&zstd.Codec{Level: zstd.SpeedDefault}),
			parquet.PageBufferSize(2 * 1024 * 1024), // 2MB
			parquet.MaxRowsPerRowGroup(1000),        // Flush every 1000 rows
			parquet.DataPageStatistics(false),
		}
	}

	parquetWriter := parquet.NewGenericWriter[ParquetRow](parquetFile, parquetOptions...)

	// Adjust batch size and allocations based on compression mode
	var actualBatchSize int
	var builderSize int
	var queriesCapacity int

	switch compressionMode {
	case "low-memory":
		actualBatchSize = 100   // Small batches
		builderSize = 100 * 100 // 10KB
		queriesCapacity = 100
	case "high-compression":
		actualBatchSize = 10000   // Very large batches - accumulate more data
		builderSize = 10000 * 100 // 1MB
		queriesCapacity = 10000
	default: // "balanced"
		actualBatchSize = 1000   // Medium batches
		builderSize = 1000 * 100 // 100KB
		queriesCapacity = 1000
	}

	sqlStringBuilderForFlush := strings.Builder{}
	sqlStringBuilderForFlush.Grow(builderSize)

	return &BinlogIndexer{
		BatchSize:                actualBatchSize,
		binlogName:               binlogFilename,
		binlogPath:               binlogPath,
		compressionMode:          compressionMode,
		queries:                  make([]Query, 0, queriesCapacity),
		currentRowId:             1,
		estimatedMemory:          0,
		db:                       db,
		fw:                       parquetFile,
		pw:                       parquetWriter,
		parser:                   replication.NewBinlogParser(),
		sqlParser:                sql_parser,
		sqlStringBuilderForFlush: sqlStringBuilderForFlush,
		isClosed:                 false,
		stringCache:              make(map[string]string),
		tableMapEvents:           make([][]string, 0, 4), // Most queries affect 1-4 tables
	}, nil
}

// internString deduplicates strings to reduce memory usage
// Database and table names are repeated frequently across events
func (p *BinlogIndexer) internString(s string) string {
	if s == "" {
		return ""
	}
	if interned, exists := p.stringCache[s]; exists {
		return interned
	}
	p.stringCache[s] = s
	return s
}

// bytesToString converts []byte to string efficiently
func (p *BinlogIndexer) bytesToString(b []byte) string {
	return p.internString(string(b))
}

// detectQueryType quickly detects SQL statement type from prefix
// This is much faster than full SQL parsing - uses byte comparison
func detectQueryType(sql string) StatementType {
	// Skip leading whitespace
	i := 0
	for i < len(sql) && (sql[i] == ' ' || sql[i] == '\t' || sql[i] == '\n' || sql[i] == '\r') {
		i++
	}

	if i >= len(sql) {
		return Other
	}

	// Fast byte-level comparison (case-insensitive)
	// Check first character to quickly filter
	firstChar := sql[i] | 0x20 // Convert to lowercase
	switch firstChar {
	case 's': // SELECT
		if i+6 <= len(sql) {
			word := sql[i : i+6]
			if strings.EqualFold(word, "SELECT") {
				return Select
			}
		}
	case 'i': // INSERT
		if i+6 <= len(sql) {
			word := sql[i : i+6]
			if strings.EqualFold(word, "INSERT") {
				return Insert
			}
		}
	case 'u': // UPDATE
		if i+6 <= len(sql) {
			word := sql[i : i+6]
			if strings.EqualFold(word, "UPDATE") {
				return Update
			}
		}
	case 'd': // DELETE
		if i+6 <= len(sql) {
			word := sql[i : i+6]
			if strings.EqualFold(word, "DELETE") {
				return Delete
			}
		}
	}

	return Other
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
			p.tableMapEvents = append(p.tableMapEvents, []string{
				p.bytesToString(event.Schema),
				p.bytesToString(event.Table),
			})
			p.annotateRowsEventSize += e.Header.EventSize
		}
	case replication.WRITE_ROWS_EVENTv1, replication.UPDATE_ROWS_EVENTv1, replication.DELETE_ROWS_EVENTv1:
		if _, ok := e.Event.(*replication.RowsEvent); ok {
			p.annotateRowsEventSize += e.Header.EventSize
		}
	case replication.QUERY_EVENT:
		if event, ok := e.Event.(*replication.QueryEvent); ok {
			sqlQuery := string(event.Query)
			schema := p.bytesToString(event.Schema)

			q := Query{
				Timestamp: e.Header.Timestamp,
				RowId:     p.currentRowId,
				EventSize: e.Header.EventSize,
				SQL:       sqlQuery,
			}

			queryType := detectQueryType(sqlQuery)
			q.Metadata = *p.ExtractSQLMetadata(queryType, sqlQuery, schema)

			p.estimatedMemory += int64(len(sqlQuery) + 32)
			p.queries = append(p.queries, q)
			p.currentRowId += 1
			p.flushIfNeeded()
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

	sqlQuery := string(p.annotateRowsEvent.Query)
	// For annotate rows events, we already have table info from TABLE_MAP_EVENT
	// Skip expensive SQL parsing and use the table map directly
	metadata := SQLSourceMetadata{
		Type:   detectQueryType(sqlQuery), // Fast prefix detection, no parsing
		Tables: make([]*SQLTable, 0, len(p.tableMapEvents)),
	}
	for _, table := range p.tableMapEvents {
		metadata.Tables = append(metadata.Tables, &SQLTable{
			Database: table[0],
			Table:    table[1],
		})
	}

	query := Query{
		Timestamp: p.annotateRowsEventTimestamp,
		Metadata:  metadata,
		RowId:     p.currentRowId,
		EventSize: p.annotateRowsEventSize,
		SQL:       sqlQuery,
	}

	// Track memory usage
	p.estimatedMemory += int64(len(sqlQuery) + 32) // SQL + struct overhead
	p.queries = append(p.queries, query)
	p.currentRowId += 1

	// reset
	p.annotateRowsEvent = nil
	p.annotateRowsEventSize = 0
	p.annotateRowsEventTimestamp = 0
	p.tableMapEvents = p.tableMapEvents[:0]

	p.flushIfNeeded()
}

func (p *BinlogIndexer) flushIfNeeded() {
	// Memory threshold varies by compression mode
	var maxMemoryBytes int64
	switch p.compressionMode {
	case "low-memory":
		maxMemoryBytes = 2 * 1024 * 1024 // 2MB - very aggressive flushing
	case "high-compression":
		maxMemoryBytes = 100 * 1024 * 1024 // 100MB - accumulate more for better compression
	default: // "balanced"
		maxMemoryBytes = 10 * 1024 * 1024 // 10MB - moderate flushing
	}

	if len(p.queries) >= p.BatchSize || p.estimatedMemory > maxMemoryBytes {
		err := p.flush()
		if err != nil {
			fmt.Printf("[WARN] failed to flush: %v\n", err)
		}
	}
}

func (p *BinlogIndexer) flush() error {
	// Create transaction
	tx, err := p.db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin db transaction: %w", err)
	}

	defer func() {
		// In case of error rollback changes
		_ = tx.Rollback()
	}()

	// Write the queries to db using strings.Builder for efficiency
	// Estimate size: each row is ~100 bytes on average

	// Count total rows for pre-allocation
	totalRows := 0
	for i := range p.queries {
		totalRows += len(p.queries[i].Metadata.Tables)
	}

	// Reset the string builder
	p.sqlStringBuilderForFlush.Reset()

	p.sqlStringBuilderForFlush.Grow(totalRows * 100) // Pre-allocate to avoid reallocations

	first := true
	if len(p.queries) == 0 {
		return nil
	}

	// Write the query template at the start
	p.sqlStringBuilderForFlush.WriteString(INSERT_QUERY_SQL)

	// Build the values
	for i := range p.queries {
		query := &p.queries[i] // avoid copy

		for j := range query.Metadata.Tables {
			table := query.Metadata.Tables[j] // avoid copy

			if !first {
				p.sqlStringBuilderForFlush.WriteByte(',')
			}
			first = false

			// Manually build the string to avoid fmt.Sprintf allocations
			p.sqlStringBuilderForFlush.WriteString("('")
			p.sqlStringBuilderForFlush.WriteString(p.binlogName)
			p.sqlStringBuilderForFlush.WriteString("', '")
			p.sqlStringBuilderForFlush.WriteString(table.Database)
			p.sqlStringBuilderForFlush.WriteString("', '")
			p.sqlStringBuilderForFlush.WriteString(table.Table)
			p.sqlStringBuilderForFlush.WriteString("', ")
			p.sqlStringBuilderForFlush.WriteString(itoa(int(query.Timestamp)))
			p.sqlStringBuilderForFlush.WriteString(", '")
			p.sqlStringBuilderForFlush.WriteString(string(query.Metadata.Type))
			p.sqlStringBuilderForFlush.WriteString("', ")
			p.sqlStringBuilderForFlush.WriteString(itoa(int(query.RowId)))
			p.sqlStringBuilderForFlush.WriteString(", ")
			p.sqlStringBuilderForFlush.WriteString(itoa(int(query.EventSize)))
			p.sqlStringBuilderForFlush.WriteByte(')')
		}
	}

	// Insert the queries
	_, err = tx.Exec(p.sqlStringBuilderForFlush.String())
	if err != nil {
		return fmt.Errorf("failed to insert queries: %w", err)
	}

	// Write to parquet file by bulk insert
	if cap(p.parquetBuffer) < len(p.queries) {
		p.parquetBuffer = make([]ParquetRow, len(p.queries))
	} else {
		p.parquetBuffer = p.parquetBuffer[:len(p.queries)]
	}

	// Fill buffer
	for i := range p.queries {
		p.parquetBuffer[i].Id = p.queries[i].RowId
		p.parquetBuffer[i].Query = p.queries[i].SQL
	}

	// Batch write
	if _, err = p.pw.Write(p.parquetBuffer); err != nil {
		return err
	}

	// Commit the transaction
	err = tx.Commit()
	if err != nil {
		return fmt.Errorf("failed to commit db transaction: %w", err)
	}

	// Clear the queries - reuse slice capacity if reasonable
	p.estimatedMemory = 0
	p.queries = p.queries[:0]

	// If slice grew too large, reset it to prevent holding too much memory
	if cap(p.queries) > p.BatchSize*2 {
		p.queries = make([]Query, 0, p.BatchSize)
	}

	// Clear string cache based on compression mode
	switch p.compressionMode {
	case "low-memory":
		// Aggressive cache clearing for low-memory mode
		if len(p.stringCache) > 1000 {
			p.stringCache = make(map[string]string, 100)
		}
		// Force GC to release memory immediately - acceptable since speed is not priority
		runtime.GC()
	case "high-compression":
		// Never clear cache in high-compression mode - maximize reuse
		// No manual GC - let Go handle it naturally
	default: // "balanced"
		// More relaxed cache clearing for balanced mode
		if len(p.stringCache) > 10000 {
			p.stringCache = make(map[string]string, 1000)
		}
		// No manual GC in balanced mode - let Go handle it
	}

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
	if err := p.pw.Close(); err != nil {
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

	// Free memory
	p.queries = nil
	p.tableMapEvents = nil
	p.stringCache = nil

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

// itoa is a faster integer to string conversion for SQL building
func itoa(i int) string {
	return strconv.Itoa(i)
}
