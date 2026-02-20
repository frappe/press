package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
)

type arrayFlags []string

func (i *arrayFlags) String() string {
	return fmt.Sprint(*i)
}

func (i *arrayFlags) Set(value string) error {
	*i = append(*i, value)
	return nil
}

func main() {
	ioWaitThreshold := flag.Float64("io-wait-threshold", 50.0, "CPU IO wait threshold percentage to pause execution")
	ioOpsLimit := flag.Float64("io-ops-limit", 200.0, "Max IO operations per second")
	parallel := flag.Int("parallel", 1, "Number of parallel workers")

	var excludeFlags arrayFlags
	flag.Var(&excludeFlags, "exclude", "Regex pattern to exclude files (can be specified multiple times)")

	flag.Parse()

	args := flag.Args()
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: go run . [--io-wait-threshold=50.0] [--io-ops-limit=200] [--parallel=1] [--exclude=pattern] <path>")
		return
	}
	inputPath := strings.Join(args, " ")

	// Compile exclude regexes
	var excludeRegexps []*regexp.Regexp
	for _, pattern := range excludeFlags {
		re, err := regexp.Compile(pattern)
		if err != nil {
			printErrorAndExit(fmt.Sprintf("Invalid regex pattern '%s': %v", pattern, err))
		}
		excludeRegexps = append(excludeRegexps, re)
	}

	var results []Output

	info, err := os.Stat(inputPath)
	if err != nil {
		printErrorAndExit(err.Error())
	}

	if info.IsDir() {
		jobs := make(chan string)
		resultsChan := make(chan Output)
		var wg sync.WaitGroup

		// Start workers
		for i := 0; i < *parallel; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for path := range jobs {
					res, err := processFile(path, *ioWaitThreshold, *ioOpsLimit)
					if err == nil {
						resultsChan <- *res
					}
				}
			}()
		}

		// Close results channel when workers are done
		go func() {
			wg.Wait()
			close(resultsChan)
		}()

		// Collect results
		done := make(chan struct{})
		go func() {
			for res := range resultsChan {
				results = append(results, res)
			}
			close(done)
		}()

		err := filepath.Walk(inputPath, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}
			if !info.IsDir() {
				if strings.HasSuffix(path, ".ibd") || strings.HasSuffix(path, ".MYD") {
					baseName := filepath.Base(path)
					exclude := false
					for _, re := range excludeRegexps {
						if re.MatchString(baseName) {
							exclude = true
							break
						}
					}

					if !exclude {
						jobs <- path
					}
				}
			}
			return nil
		})
		close(jobs)

		if err != nil {
			printErrorAndExit(err.Error())
		}
		<-done
	} else {
		baseName := filepath.Base(inputPath)
		for _, re := range excludeRegexps {
			if re.MatchString(baseName) {
				printJSONList(results)
				return
			}
		}

		res, err := processFile(inputPath, *ioWaitThreshold, *ioOpsLimit)
		if err != nil {
			printErrorAndExit(err.Error())
		}
		results = append(results, *res)
	}

	printJSONList(results)
}

func processFile(path string, ioThreshold float64, ioOpsLimit float64) (*Output, error) {
	parser, engine, file, err := getParser(path, ioThreshold, ioOpsLimit)
	if err != nil {
		return nil, err
	}
	defer func() {
		if closer, ok := parser.(interface{ Close() }); ok {
			closer.Close()
		}
	}()

	if err := parser.Run(); err != nil {
		return nil, err
	}

	dl, il, df := parser.GetStats()
	return &Output{
		DataLength:  dl,
		IndexLength: il,
		DataFree:    df,
		Engine:      engine,
		Filename:    file,
	}, nil
}

func getParser(path string, ioThreshold float64, ioOpsLimit float64) (Parser, string, string, error) {
	if strings.HasSuffix(path, ".ibd") {
		p, err := NewInnoDBParserWithRateLimit(path, ioThreshold, ioOpsLimit)
		return p, "InnoDB", path, err
	}
	if strings.HasSuffix(path, ".MYD") {
		myiPath := strings.TrimSuffix(path, ".MYD") + ".MYI"
		return NewMyISAMParser(path, myiPath), "MyISAM", path, nil
	}

	// Try finding InnoDB file (.ibd)
	ibdName := path + ".ibd"
	if _, err := os.Stat(ibdName); err == nil {
		p, err := NewInnoDBParserWithRateLimit(ibdName, ioThreshold, ioOpsLimit)
		return p, "InnoDB", ibdName, err
	}

	// Try finding MyISAM files
	if _, err := os.Stat(path + ".MYD"); err == nil {
		mydPath := path + ".MYD"
		myiPath := path + ".MYI"
		return NewMyISAMParser(mydPath, myiPath), "MyISAM", mydPath, nil
	}

	return nil, "", "", fmt.Errorf("unsupported file type or file not found: %s", path)
}

func printJSONList(out []Output) {
	b, err := json.MarshalIndent(out, "", "  ")
	if err != nil {
		printErrorAndExit(err.Error())
	}
	fmt.Println(string(b))
}

func printErrorAndExit(msg string) {
	type ErrorOutput struct {
		Error string `json:"error"`
	}
	b, _ := json.MarshalIndent(ErrorOutput{Error: msg}, "", "  ")
	fmt.Fprintln(os.Stderr, string(b))
	os.Exit(1)
}
