package main

import (
	_ "embed"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
)

const (
	defaultBinaryPath  = "/usr/local/bin/mariadb-monitor"
	defaultServicePath = "/etc/systemd/system/mariadb-monitor.service"
)

//go:embed mariadb-monitor.service
var serviceFileContent string

func install() error {
	if os.Geteuid() != 0 {
		return fmt.Errorf("install must be run as root")
	}

	if _, err := os.Stat(myCnfPath); os.IsNotExist(err) {
		return fmt.Errorf("%s not found — create it with [client] section containing user, password, and socket", myCnfPath)
	}

	self, err := os.Executable()
	if err != nil {
		return fmt.Errorf("cannot determine own path: %w", err)
	}
	self, err = filepath.EvalSymlinks(self)
	if err != nil {
		return fmt.Errorf("cannot resolve own path: %w", err)
	}

	slog.Info("copying binary", "from", self, "to", defaultBinaryPath)
	data, err := os.ReadFile(self)
	if err != nil {
		return fmt.Errorf("read binary: %w", err)
	}
	if err := os.WriteFile(defaultBinaryPath, data, 0755); err != nil {
		return fmt.Errorf("write binary: %w", err)
	}

	if _, err := os.Stat(configFile); os.IsNotExist(err) {
		slog.Info("generating default config", "path", configFile)
		if err := GenerateDefaultConfig(); err != nil {
			return fmt.Errorf("generate config: %w", err)
		}
	} else {
		slog.Info("config already exists, skipping", "path", configFile)
	}

	slog.Info("creating log directory", "path", logDir)
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return fmt.Errorf("create log dir: %w", err)
	}

	slog.Info("installing systemd service", "path", defaultServicePath)
	if err := os.WriteFile(defaultServicePath, []byte(serviceFileContent), 0644); err != nil {
		return fmt.Errorf("write service file: %w", err)
	}

	if out, err := exec.Command("systemctl", "daemon-reload").CombinedOutput(); err != nil {
		return fmt.Errorf("daemon-reload: %w (%s)", err, string(out))
	}
	if out, err := exec.Command("systemctl", "enable", "--now", "mariadb-monitor").CombinedOutput(); err != nil {
		return fmt.Errorf("enable and start service: %w (%s)", err, string(out))
	}

	slog.Info("installation complete")
	fmt.Println("✓ Binary installed to", defaultBinaryPath)
	fmt.Println("✓ Config at", configFile)
	fmt.Println("✓ Logs at", logFile)
	fmt.Println("✓ Systemd service installed, enabled, and started")
	fmt.Println("")
	fmt.Println("Check status: systemctl status mariadb-monitor")
	fmt.Println("Logs:         /var/log/mariadb-monitor/monitor.log")
	return nil
}

func uninstall() error {
	if os.Geteuid() != 0 {
		return fmt.Errorf("uninstall must be run as root")
	}

	slog.Info("stopping and disabling service")
	exec.Command("systemctl", "stop", "mariadb-monitor").Run()
	exec.Command("systemctl", "disable", "mariadb-monitor").Run()

	if err := os.Remove(defaultServicePath); err != nil && !os.IsNotExist(err) {
		slog.Warn("failed to remove service file", "error", err)
	} else {
		slog.Info("removed service file", "path", defaultServicePath)
	}

	exec.Command("systemctl", "daemon-reload").Run()

	if err := os.Remove(defaultBinaryPath); err != nil && !os.IsNotExist(err) {
		slog.Warn("failed to remove binary", "error", err)
	} else {
		slog.Info("removed binary", "path", defaultBinaryPath)
	}

	fmt.Println("✓ Service stopped and disabled")
	fmt.Println("✓ Binary removed from", defaultBinaryPath)
	fmt.Println("✓ Service file removed")
	fmt.Println("")
	fmt.Println("Config preserved at", configFile, "(remove manually if desired)")
	return nil
}
