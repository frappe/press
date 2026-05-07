package main

import (
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	if len(os.Args) > 1 {
		slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
			Level: slog.LevelInfo,
		})))

		switch os.Args[1] {
		case "run":
		case "install":
			if err := install(); err != nil {
				slog.Error("install failed", "error", err)
				os.Exit(1)
			}
			return
		case "uninstall":
			if err := uninstall(); err != nil {
				slog.Error("uninstall failed", "error", err)
				os.Exit(1)
			}
			return
		case "help", "-h", "--help":
			printHelp()
			return
		default:
			fmt.Fprintf(os.Stderr, "Unknown command: %s\n", os.Args[1])
			printHelp()
			os.Exit(1)
		}
	}

	if _, err := os.Stat(configFile); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "config not found, generating default at %s\n", configFile)
		if err := GenerateDefaultConfig(); err != nil {
			fmt.Fprintf(os.Stderr, "WARNING: could not generate default config: %v\n", err)
		}
	}

	cfg, err := LoadConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: failed to load config from %s: %v\n", configFile, err)
		os.Exit(1)
	}

	logWriter, err := setupLogging(cfg.LogLevel)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: failed to set up logging: %v\n", err)
		os.Exit(1)
	}
	defer logWriter.Close()

	creds, err := LoadMySQLCredentials()
	if err != nil {
		slog.Error("failed to load mysql credentials", "path", myCnfPath, "error", err)
		fmt.Fprintf(os.Stderr, "ERROR: %s is required with [client] section for user, password, and socket.\n", myCnfPath)
		os.Exit(1)
	}

	slog.Info("mariadb monitor starting",
		"check_interval", cfg.CheckInterval,
		"window_size", cfg.Monitor.WindowSize,
		"sustained_ratio", cfg.Monitor.SustainedRatio,
		"mariadb_socket", creds.Socket,
		"mariadb_user", creds.User,
		"log_level", cfg.LogLevel,
		"log_file", logFile,
		"max_recoveries_per_hour", cfg.Monitor.MaxRecoveriesPerHour,
		"drop_caches_mode", cfg.Monitor.DropCachesMode,
	)

	mon := newMonitor(cfg, creds)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	mon.run(sigCh)
}

func printHelp() {
	fmt.Println("MariaDB Monitor")
	fmt.Println("")
	fmt.Println("Usage:")
	fmt.Println("  mariadb-monitor [command]")
	fmt.Println("")
	fmt.Println("Commands:")
	fmt.Println("  run        Run the monitor directly (default)")
	fmt.Println("  install    Install the monitor as a systemd service")
	fmt.Println("  uninstall  Remove the monitor systemd service")
	fmt.Println("  help       Show this help message")
	fmt.Println("")
	fmt.Println("When run without arguments, the monitor runs in the foreground.")
}
