package main

import (
	"database/sql"
	"os"
	"path/filepath"
	"testing"
)

func newTestIndexer(t *testing.T) *BinlogIndexer {
	t.Helper()
	basePath := t.TempDir()
	indexer, err := NewBinlogIndexer(basePath, filepath.Join(basePath, "mysql-bin.000001"), "queries.db", "low-memory")
	if err != nil {
		t.Fatalf("NewBinlogIndexer: %v", err)
	}
	t.Cleanup(indexer.Close)
	return indexer
}

func countIndexedRows(t *testing.T, indexer *BinlogIndexer) int {
	t.Helper()
	var count int
	if err := indexer.db.QueryRow("SELECT count(*) FROM query").Scan(&count); err != nil {
		t.Fatalf("count rows: %v", err)
	}
	return count
}

// A new server's first binlog holds only account statements (CREATE USER, GRANT) run with no
// default database. None of them yields a table, so a batch can have queries but no rows to insert.
func TestFlushBatchWithoutTables(t *testing.T) {
	indexer := newTestIndexer(t)
	for _, sql := range []string{
		"CREATE USER 'monitor'@'%' IDENTIFIED BY 'x'",
		"GRANT SELECT ON `sys`.* TO 'monitor'@'%'",
	} {
		indexer.queries = append(indexer.queries, Query{
			RowId:    indexer.currentRowId,
			Metadata: *indexer.ExtractSQLMetadata(detectQueryType(sql), sql, ""),
			SQL:      sql,
		})
		indexer.currentRowId++
	}

	if err := indexer.flush(); err != nil {
		t.Fatalf("flush: %v", err)
	}
	if len(indexer.queries) != 0 {
		t.Fatalf("flushed queries were not cleared: %d left", len(indexer.queries))
	}
	if n := countIndexedRows(t, indexer); n != 0 {
		t.Fatalf("expected no indexed rows, got %d", n)
	}
}

// Queries with tables in the same batch as table-less ones are still indexed.
func TestFlushMixedBatch(t *testing.T) {
	indexer := newTestIndexer(t)
	for _, q := range []struct{ sql, schema string }{
		{"GRANT ALL ON *.* TO 'root'@'%'", ""},
		{"INSERT INTO `tabNote` (`name`) VALUES ('a')", "_site_db"},
		{"UPDATE `tabNote` SET `title` = 'b'", "_site_db"},
	} {
		indexer.queries = append(indexer.queries, Query{
			RowId:    indexer.currentRowId,
			Metadata: *indexer.ExtractSQLMetadata(detectQueryType(q.sql), q.sql, q.schema),
			SQL:      q.sql,
		})
		indexer.currentRowId++
	}

	if err := indexer.flush(); err != nil {
		t.Fatalf("flush: %v", err)
	}
	if n := countIndexedRows(t, indexer); n != 2 {
		t.Fatalf("expected 2 indexed rows, got %d", n)
	}
}

func indexedBinlogs(t *testing.T, basePath string) []string {
	t.Helper()
	db, err := sql.Open("duckdb", filepath.Join(basePath, "queries.db"))
	if err != nil {
		t.Fatalf("open index: %v", err)
	}
	defer db.Close()
	rows, err := db.Query("SELECT binlog FROM indexed_binlog ORDER BY binlog")
	if err != nil {
		t.Fatalf("query indexed_binlog: %v", err)
	}
	defer rows.Close()
	var names []string
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			t.Fatalf("scan: %v", err)
		}
		names = append(names, name)
	}
	return names
}

// A binlog with no indexable query leaves no rows in the query table, yet must be reported as
// indexed, or it is queued for indexing again forever.
func TestStartRecordsBinlogWithoutQueries(t *testing.T) {
	basePath := t.TempDir()
	binlogPath := filepath.Join(basePath, "mysql-bin.000003")
	if err := os.WriteFile(binlogPath, []byte{0xfe, 'b', 'i', 'n'}, 0o644); err != nil {
		t.Fatalf("write binlog: %v", err)
	}

	indexer, err := NewBinlogIndexer(basePath, binlogPath, "queries.db", "low-memory")
	if err != nil {
		t.Fatalf("NewBinlogIndexer: %v", err)
	}
	if err := indexer.Start(); err != nil {
		t.Fatalf("Start: %v", err)
	}
	if got := indexedBinlogs(t, basePath); len(got) != 1 || got[0] != "mysql-bin.000003" {
		t.Fatalf("expected mysql-bin.000003 recorded as indexed, got %v", got)
	}

	if err := RemoveBinlogIndex(basePath, binlogPath, "queries.db"); err != nil {
		t.Fatalf("RemoveBinlogIndex: %v", err)
	}
	if got := indexedBinlogs(t, basePath); len(got) != 0 {
		t.Fatalf("expected no indexed binlogs after removal, got %v", got)
	}
}
