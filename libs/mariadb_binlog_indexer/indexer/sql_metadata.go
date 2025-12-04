package main

import (
	"fmt"

	"vitess.io/vitess/go/vt/sqlparser"
)

// StatementType represents the type of SQL statement
type StatementType string

const (
	Select StatementType = "SELECT"
	Insert StatementType = "INSERT"
	Update StatementType = "UPDATE"
	Delete StatementType = "DELETE"
	Other  StatementType = "OTHER"
)

type SQLTable struct {
	Database string
	Table    string // Can be blank for OTHER queries
}

// SQLSourceMetadata contains the parsed SQL information
type SQLSourceMetadata struct {
	Type   StatementType // The type of SQL statement
	Tables []*SQLTable   // The database and table
}

func (r *SQLSourceMetadata) Reset() {
	// Clear slice without freeing underlying array
	r.Tables = r.Tables[:0]
	r.Type = Other
}

func (r SQLSourceMetadata) String() string {
	tablesString := ""
	for _, table := range r.Tables {
		if table.Database == "" {
			tablesString += fmt.Sprintf("`%s`, ", table.Table)
			continue
		}
		tablesString += fmt.Sprintf("`%s`.`%s`, ", table.Database, table.Table)
	}
	return fmt.Sprintf("Type: %s\tTables: %s", r.Type, tablesString)
}

// StringInterner interface for string deduplication
type StringInterner interface {
	internString(s string) string
}

// ExtractSQLMetadata extracts database/table pairs and statement type from SQL
func (b *BinlogIndexer) ExtractSQLMetadata(stmtType StatementType, sql string, defaultDatabase string) *SQLSourceMetadata {
	result := &SQLSourceMetadata{
		Tables: make([]*SQLTable, 0, 2),
		Type:   Other,
	}
	stmt, err := b.sqlParser.Parse(sql)
	if err != nil {
		return result
	}

	internedDefault := ""
	if defaultDatabase != "" {
		internedDefault = b.internString(defaultDatabase)
	}

	if stmtType != Other {

		// Instead of walking the AST, we only care about top-level table references
		switch node := stmt.(type) {
		case *sqlparser.Select:
			result.Type = Select
			for _, tableExpr := range node.From {
				b.extractTable(tableExpr, result, internedDefault)
			}

		case *sqlparser.Insert:
			result.Type = Insert
			if table, err := node.Table.TableName(); err == nil {
				result.Tables = append(result.Tables, b.makeTable(table, internedDefault))
			}

		case *sqlparser.Update:
			result.Type = Update
			for _, tableExpr := range node.TableExprs {
				b.extractTable(tableExpr, result, internedDefault)
			}

		case *sqlparser.Delete:
			result.Type = Delete
			for _, tableExpr := range node.TableExprs {
				b.extractTable(tableExpr, result, internedDefault)
			}
		}
	}

	// Fallback if no tables extracted
	if len(result.Tables) == 0 && internedDefault != "" {
		result.Tables = []*SQLTable{{Database: internedDefault, Table: ""}}
	}

	return result
}

func (b *BinlogIndexer) extractTable(tableExpr sqlparser.TableExpr, result *SQLSourceMetadata, defaultDB string) {
	if aliasedTable, ok := tableExpr.(*sqlparser.AliasedTableExpr); ok {
		if table, err := aliasedTable.TableName(); err == nil {
			result.Tables = append(result.Tables, b.makeTable(table, defaultDB))
		}
	}
}

func (b *BinlogIndexer) makeTable(table sqlparser.TableName, defaultDB string) *SQLTable {
	db := table.Qualifier.String()
	if db == "" {
		db = defaultDB
	} else {
		db = b.internString(db)
	}

	return &SQLTable{
		Database: db,
		Table:    b.internString(table.Name.String()),
	}
}
