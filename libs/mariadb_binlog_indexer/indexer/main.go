package main

import (
	"fmt"
	"os"
	"strconv"
)

func main() {
	if len(os.Args) < 5 {
		fmt.Println("Usage: mariadb_binlog_indexer <add/remove> <base_path> <binlog_path> <database_name> <batch_size = 10000>")
		return
	}

	if os.Args[1] == "add" {
		batchSize := 10000
		if len(os.Args) == 6 {
			batchSizeCmd, err := strconv.Atoi(os.Args[5])
			if err != nil {
				fmt.Println("Invalid batch size")
				os.Exit(1)
			}
			batchSize = batchSizeCmd
		}
		indexer, err := NewBinlogIndexer(
			os.Args[2],
			os.Args[3],
			os.Args[4],
			batchSize,
		)
		if err != nil {
			fmt.Println(err.Error())
			os.Exit(1)
		}
		defer func() {
			indexer.Close()
		}()
		err = indexer.Start()
		if err != nil {
			fmt.Println(err.Error())
			os.Exit(1)
		}
	} else if os.Args[1] == "remove" {
		err := RemoveBinlogIndex(
			os.Args[2],
			os.Args[3],
			os.Args[4],
		)
		if err != nil {
			fmt.Println(err.Error())
			os.Exit(1)
		}
	} else {
		fmt.Println("Invalid command")
		os.Exit(1)
	}
}
