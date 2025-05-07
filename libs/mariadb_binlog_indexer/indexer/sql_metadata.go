package main

import (
	"fmt"
	"strings"

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

// ExtractSQLMetadata extracts database/table pairs and statement type from SQL
func ExtractSQLMetadata(sql string, parser *sqlparser.Parser, defaultDatabase string) SQLSourceMetadata {
	result := SQLSourceMetadata{
		Tables: []*SQLTable{},
		Type:   Other,
	}

	stmt, err := parser.Parse(sql)
	if err != nil {
		return result
	}

	sqlparser.Walk(func(node sqlparser.SQLNode) (kontinue bool, err error) {
		switch node := node.(type) {
		case *sqlparser.Select:
			result.Type = Select
			for _, table := range node.From {
				if tblExpr, ok := table.(*sqlparser.AliasedTableExpr); ok {
					if table, err := tblExpr.TableName(); err == nil {
						result.Tables = append(result.Tables, &SQLTable{
							Database: table.Qualifier.String(),
							Table:    table.Name.String(),
						})
					}
				}
			}
			return false, nil

		case *sqlparser.Insert:
			result.Type = Insert
			if table, err := node.Table.TableName(); err == nil {
				result.Tables = append(result.Tables, &SQLTable{
					Database: table.Qualifier.String(),
					Table:    table.Name.String(),
				})
			}
			return false, nil

		case *sqlparser.Delete:
			result.Type = Delete
			for _, expr := range node.TableExprs {
				if tblExpr, ok := expr.(*sqlparser.AliasedTableExpr); ok {
					if table, err := tblExpr.TableName(); err == nil {
						result.Tables = append(result.Tables, &SQLTable{
							Database: table.Qualifier.String(),
							Table:    table.Name.String(),
						})
					}
				}
			}
			return false, nil

		case *sqlparser.Update:
			result.Type = Update
			for _, expr := range node.TableExprs {
				if tblExpr, ok := expr.(*sqlparser.AliasedTableExpr); ok {
					if table, err := tblExpr.TableName(); err == nil {
						result.Tables = append(result.Tables, &SQLTable{
							Database: table.Qualifier.String(),
							Table:    table.Name.String(),
						})
					}
				}
			}
			return false, nil
		}

		return true, nil
	}, stmt)

	// Set default database if database is empty
	if defaultDatabase != "" {
		for _, table := range result.Tables {
			if strings.Compare(table.Database, "") == 0 {
				table.Database = defaultDatabase
			}
		}
	}

	// If result is empty, set default database
	if len(result.Tables) == 0 && defaultDatabase != "" {
		result.Tables = []*SQLTable{
			{
				Database: defaultDatabase,
				Table:    "",
			},
		}
	}

	return result
}
