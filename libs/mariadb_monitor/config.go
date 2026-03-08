package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

const (
	configDir  = "/etc/mariadb-monitor"
	configFile = "/etc/mariadb-monitor/config.yaml"
	myCnfPath  = "/root/.my.cnf"
)

type Config struct {
	LogLevel              string        `yaml:"log_level"`
	CheckInterval         time.Duration `yaml:"check_interval"`
	CooldownAfterRecovery time.Duration `yaml:"cooldown_after_recovery"`
	StopTimeout           time.Duration `yaml:"stop_timeout"`

	WindowSize     int     `yaml:"window_size"`
	SustainedRatio float64 `yaml:"sustained_ratio"`

	PSICPUThreshold    float64 `yaml:"psi_cpu_threshold"`
	PSIMemoryThreshold float64 `yaml:"psi_memory_threshold"`
	PSIIOThreshold     float64 `yaml:"psi_io_threshold"`

	IOWaitThreshold         float64       `yaml:"iowait_threshold"`
	MemoryUsageThreshold    float64       `yaml:"memory_usage_threshold"`
	CriticalMemoryThreshold float64       `yaml:"critical_memory_threshold"`
	SwapUsageThreshold      float64       `yaml:"swap_usage_threshold"`
	SwapHeadroom            float64       `yaml:"swap_headroom"`
	PageRateThreshold       float64       `yaml:"page_rate_threshold"`
	IOFreezeTimeout         time.Duration `yaml:"io_freeze_timeout"`

	StuckQueryThreshold time.Duration `yaml:"stuck_query_threshold"`

	MaxRecoveriesPerHour int `yaml:"max_recoveries_per_hour"`
	DropCachesMode       int `yaml:"drop_caches_mode"`
}

type MySQLCredentials struct {
	User     string
	Password string
	Socket   string
}

func DefaultConfig() Config {
	return Config{
		LogLevel:                "WARN",
		CheckInterval:           5 * time.Second,
		CooldownAfterRecovery:   120 * time.Second,
		StopTimeout:             30 * time.Second,
		WindowSize:              12,
		SustainedRatio:          0.7,
		PSICPUThreshold:         80.0,
		PSIMemoryThreshold:      60.0,
		PSIIOThreshold:          60.0,
		IOWaitThreshold:         50.0,
		MemoryUsageThreshold:    95.0,
		CriticalMemoryThreshold: 98.0,
		SwapUsageThreshold:      80.0,
		SwapHeadroom:            10.0,
		PageRateThreshold:       100000,
		IOFreezeTimeout:         5 * time.Second,
		StuckQueryThreshold:     30 * time.Second,
		MaxRecoveriesPerHour:    3,
		DropCachesMode:          1,
	}
}

func LoadConfig() (Config, error) {
	cfg := DefaultConfig()

	data, err := os.ReadFile(configFile)
	if err != nil {
		if os.IsNotExist(err) {
			return cfg, nil
		}
		return cfg, err
	}

	var raw map[string]interface{}
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return cfg, err
	}

	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return cfg, err
	}

	parseDuration(raw, "check_interval", &cfg.CheckInterval)
	parseDuration(raw, "cooldown_after_recovery", &cfg.CooldownAfterRecovery)
	parseDuration(raw, "stop_timeout", &cfg.StopTimeout)
	parseDuration(raw, "io_freeze_timeout", &cfg.IOFreezeTimeout)
	parseDuration(raw, "stuck_query_threshold", &cfg.StuckQueryThreshold)

	return cfg, nil
}

func LoadMySQLCredentials() (MySQLCredentials, error) {
	creds := MySQLCredentials{
		User:   "root",
		Socket: "/var/run/mysqld/mysqld.sock",
	}

	f, err := os.Open(myCnfPath)
	if err != nil {
		return creds, fmt.Errorf("cannot open %s: %w", myCnfPath, err)
	}
	defer f.Close()

	inClientSection := false
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, ";") {
			continue
		}

		if strings.HasPrefix(line, "[") {
			inClientSection = strings.EqualFold(line, "[client]")
			continue
		}

		if !inClientSection {
			continue
		}

		key, value, ok := parseINILine(line)
		if !ok {
			continue
		}

		switch strings.ToLower(key) {
		case "user":
			creds.User = value
		case "password":
			creds.Password = value //pragma: allowlist secret
		case "socket":
			creds.Socket = value
		}
	}

	return creds, scanner.Err()
}

func parseINILine(line string) (key, value string, ok bool) {
	idx := strings.IndexByte(line, '=')
	if idx < 0 {
		return "", "", false
	}
	key = strings.TrimSpace(line[:idx])
	value = strings.TrimSpace(line[idx+1:])
	value = strings.Trim(value, `"'`)
	return key, value, true
}

func parseDuration(raw map[string]interface{}, key string, target *time.Duration) {
	if v, ok := raw[key]; ok {
		if s, ok := v.(string); ok {
			if d, err := time.ParseDuration(s); err == nil {
				*target = d
			}
		}
	}
}

func GenerateDefaultConfig() error {
	if err := os.MkdirAll(filepath.Dir(configFile), 0755); err != nil {
		return fmt.Errorf("create config dir: %w", err)
	}

	cfg := DefaultConfig()
	data, err := yaml.Marshal(&cfg)
	if err != nil {
		return fmt.Errorf("marshal default config: %w", err)
	}

	header := []byte("# MariaDB Monitor Configuration\n\n")
	fullData := append(header, data...)

	return os.WriteFile(configFile, fullData, 0644)
}
