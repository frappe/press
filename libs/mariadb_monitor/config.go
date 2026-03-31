package main

import (
	"bufio"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
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

	MaxRecoveriesPerHour int `yaml:"max_recoveries_per_hour"`
	DropCachesMode       int `yaml:"drop_caches_mode"`

	CoredumpEnabled            bool          `yaml:"coredump_enabled"`
	CoredumpOutputDir          string        `yaml:"coredump_output_dir"`
	CoredumpTimeout            time.Duration `yaml:"coredump_timeout"`
	CoredumpMaxCount           int           `yaml:"coredump_max_count"`
	CoredumpOnUnhealthy        bool          `yaml:"coredump_on_unhealthy"`
	CoredumpOnFrequentTriggers bool          `yaml:"coredump_on_frequent_triggers"`
	CoredumpFrequentThreshold  int           `yaml:"coredump_frequent_threshold"`
}

type MySQLCredentials struct {
	User     string
	Password string
	Socket   string
	Host     string
	Port     int
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
		MaxRecoveriesPerHour:    3,
		DropCachesMode:          1,

		CoredumpEnabled:            false,
		CoredumpOutputDir:          "/var/lib/mariadb-monitor/coredumps",
		CoredumpTimeout:            120 * time.Second,
		CoredumpMaxCount:           3,
		CoredumpOnUnhealthy:        true,
		CoredumpOnFrequentTriggers: true,
		CoredumpFrequentThreshold:  3,
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
	parseDuration(raw, "coredump_timeout", &cfg.CoredumpTimeout)

	if err := cfg.Validate(); err != nil {
		return cfg, fmt.Errorf("config validation: %w", err)
	}

	appendMissingDefaults(raw)

	return cfg, nil
}

func appendMissingDefaults(existing map[string]interface{}) {
	defaultBytes, err := yaml.Marshal(DefaultConfig())
	if err != nil {
		return
	}

	var defaultMap map[string]interface{}
	if err := yaml.Unmarshal(defaultBytes, &defaultMap); err != nil {
		return
	}

	var missing []string
	for key, val := range defaultMap {
		if _, found := existing[key]; !found {
			valBytes, err := yaml.Marshal(val)
			if err != nil {
				continue
			}
			missing = append(missing, fmt.Sprintf("%s: %s", key, strings.TrimSpace(string(valBytes))))
		}
	}

	if len(missing) == 0 {
		return
	}

	f, err := os.OpenFile(configFile, os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		slog.Warn("failed to open config for appending defaults", "error", err)
		return
	}
	defer f.Close()

	lines := "\n# Auto-appended defaults for new config options\n"
	for _, line := range missing {
		lines += line + "\n"
	}

	if _, err := f.WriteString(lines); err != nil {
		slog.Warn("failed to append missing defaults to config", "error", err)
	} else {
		slog.Info("appended missing config defaults", "keys", len(missing))
	}
}

func (c Config) Validate() error {
	if c.WindowSize <= 0 {
		return fmt.Errorf("window_size must be > 0, got %d", c.WindowSize)
	}
	if c.SustainedRatio < 0 || c.SustainedRatio > 1 {
		return fmt.Errorf("sustained_ratio must be between 0 and 1, got %.2f", c.SustainedRatio)
	}
	if c.CheckInterval <= 0 {
		return fmt.Errorf("check_interval must be > 0")
	}
	if c.MaxRecoveriesPerHour < 0 {
		return fmt.Errorf("max_recoveries_per_hour must be >= 0, got %d", c.MaxRecoveriesPerHour)
	}
	if c.DropCachesMode < 0 || c.DropCachesMode > 3 {
		return fmt.Errorf("drop_caches_mode must be 0-3, got %d", c.DropCachesMode)
	}
	if c.CoredumpEnabled && c.CoredumpOutputDir == "" {
		return fmt.Errorf("coredump_output_dir must be set when coredump_enabled is true")
	}
	if c.CoredumpMaxCount < 0 {
		return fmt.Errorf("coredump_max_count must be >= 0, got %d", c.CoredumpMaxCount)
	}
	if c.CoredumpFrequentThreshold < 1 {
		return fmt.Errorf("coredump_frequent_threshold must be >= 1, got %d", c.CoredumpFrequentThreshold)
	}
	return nil
}

func LoadMySQLCredentials() (MySQLCredentials, error) {
	creds := MySQLCredentials{
		User:   "root",
		Socket: "/var/run/mysqld/mysqld.sock",
		Host:   "127.0.0.1",
		Port:   3306,
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
		case "host":
			creds.Host = value
		case "port":
			p, err := strconv.Atoi(value)
			if err != nil {
				return creds, fmt.Errorf("invalid port %q in %s: %w", value, myCnfPath, err)
			}
			creds.Port = p
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
	content := fmt.Sprintf(`# MariaDB Monitor Configuration

log_level: %s
check_interval: %s
cooldown_after_recovery: %s
stop_timeout: %s
window_size: %d
sustained_ratio: %.1f
psi_cpu_threshold: %.0f
psi_memory_threshold: %.0f
psi_io_threshold: %.0f
iowait_threshold: %.0f
memory_usage_threshold: %.0f
critical_memory_threshold: %.0f
swap_usage_threshold: %.0f
swap_headroom: %.0f
page_rate_threshold: %.0f
io_freeze_timeout: %s
max_recoveries_per_hour: %d
drop_caches_mode: %d
`,
		cfg.LogLevel,
		cfg.CheckInterval,
		cfg.CooldownAfterRecovery,
		cfg.StopTimeout,
		cfg.WindowSize,
		cfg.SustainedRatio,
		cfg.PSICPUThreshold,
		cfg.PSIMemoryThreshold,
		cfg.PSIIOThreshold,
		cfg.IOWaitThreshold,
		cfg.MemoryUsageThreshold,
		cfg.CriticalMemoryThreshold,
		cfg.SwapUsageThreshold,
		cfg.SwapHeadroom,
		cfg.PageRateThreshold,
		cfg.IOFreezeTimeout,
		cfg.MaxRecoveriesPerHour,
		cfg.DropCachesMode,
	)

	content += fmt.Sprintf(`
# Coredump settings (gcore)
coredump_enabled: %t
coredump_output_dir: %s
coredump_timeout: %s
coredump_max_count: %d
coredump_on_unhealthy: %t
coredump_on_frequent_triggers: %t
coredump_frequent_threshold: %d
`,
		cfg.CoredumpEnabled,
		cfg.CoredumpOutputDir,
		cfg.CoredumpTimeout,
		cfg.CoredumpMaxCount,
		cfg.CoredumpOnUnhealthy,
		cfg.CoredumpOnFrequentTriggers,
		cfg.CoredumpFrequentThreshold,
	)

	return os.WriteFile(configFile, []byte(content), 0644)
}
