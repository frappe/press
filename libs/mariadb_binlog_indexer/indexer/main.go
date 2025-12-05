package main

import (
	"fmt"
	"log"
	"os"
	"runtime"
	"runtime/pprof"
)

func main() {
	if len(os.Args) < 5 {
		fmt.Println("Usage: mariadb_binlog_indexer <add/remove> <base_path> <binlog_path> <database_name> [compression_mode=balanced]")
		fmt.Println("")
		fmt.Println("Compression modes:")
		fmt.Println("  low-memory:       <150MB, slowest, Snappy, batch=100, minimal memory")
		fmt.Println("  balanced:         <300MB RSS, good speed, ZSTD default, batch=1000 (default)")
		fmt.Println("  high-compression: <1GB RSS, fastest, ZSTD max, batch=10000, smallest files")
		fmt.Println("")
		fmt.Println("Examples:")
		fmt.Println("  ./mariadb_binlog_indexer add /data /binlog queries.duckdb low-memory")
		fmt.Println("  ./mariadb_binlog_indexer add /data /binlog queries.duckdb high-compression")
		return
	}

	if os.Args[1] == "add" {
		compressionMode := "balanced" // default mode

		// Parse optional compression mode (arg 5)
		if len(os.Args) >= 6 {
			mode := os.Args[5]
			if mode != "low-memory" && mode != "balanced" && mode != "high-compression" {
				fmt.Println("Invalid compression mode. Use 'low-memory', 'balanced', or 'high-compression'")
				os.Exit(1)
			}
			compressionMode = mode
		}

		fmt.Printf("Starting indexer with compression mode: %s\n", compressionMode)

		indexer, err := NewBinlogIndexer(
			os.Args[2],
			os.Args[3],
			os.Args[4],
			compressionMode,
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

	isProfilerEnabled := os.Getenv("PPROF_ENABLED")
	if isProfilerEnabled != "1" {
		return
	}

	// Generate memory profile
	f, err := os.Create("mem.prof")
	if err != nil {
		log.Fatal("could not create memory profile: ", err)
	}
	defer f.Close()

	runtime.GC() // Force GC for accurate profile

	if err := pprof.WriteHeapProfile(f); err != nil {
		log.Fatal("could not write memory profile: ", err)
	}

	log.Println("Memory profile written to mem.prof")
}
