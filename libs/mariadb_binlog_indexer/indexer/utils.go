package main

import (
	"fmt"
	"os"

	"github.com/go-mysql-org/go-mysql/replication"
)

const NO_OF_QUERIES_IN_EACH_PARQUET_PAGE = 4000

func EstimateParquetPageSize(binlogPath string) (int64, error) {
	info, err := os.Stat(binlogPath)
	if err != nil {
		return 0, fmt.Errorf("failed to stat binlog file: %w", err)
	}
	queryCount, err := estimateQueryCountInBinlog(binlogPath)
	if err != nil {
		return 0, fmt.Errorf("failed to estimate query count in binlog: %w", err)
	}
	/*
	* We should be able to fit NO_OF_QUERIES_IN_EACH_PARQUET_PAGE queries in single page size
	* So we need to estimate the no of pages by that way
	 */
	// find no of queries in 100MB
	fileSizeInMB := max(int64(info.Size()/1024/1024), 1) // convert to MB just for simplification
	noOfQueriesIn100MB := int64((queryCount / fileSizeInMB) * 100)

	// now find out no of groups with NO_OF_QUERIES_IN_EACH_PARQUET_PAGE queries in each
	noOfGroups := max(int64(noOfQueriesIn100MB/NO_OF_QUERIES_IN_EACH_PARQUET_PAGE), 1)
	pageSize := int64(100 * 1024 * 1024 / noOfGroups)
	// it should be minimum 512KB
	pageSize = max(pageSize, 512*1024)
	return pageSize, nil
}

func estimateQueryCountInBinlog(binlogPath string) (int64, error) {
	if _, err := os.Stat(binlogPath); os.IsNotExist(err) {
		return 0, fmt.Errorf("binlog file does not exist: %w", err)
	}
	parser := replication.NewBinlogParser()

	var noOfQueries int64 = 0
	err := parser.ParseFile(binlogPath, 0, func(e *replication.BinlogEvent) error {
		if e.Header.EventType == replication.MARIADB_ANNOTATE_ROWS_EVENT || e.Header.EventType == replication.QUERY_EVENT {
			noOfQueries += 1
		}
		return nil
	})
	if err != nil {
		fmt.Printf("Failed to parse binlog: %v\n", err)
	}

	return noOfQueries, nil
}
