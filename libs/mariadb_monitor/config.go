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
	configFile = "/etc/mariadb-monitor/config.yaml"
	myCnfPath  = "/root/.my.cnf"
)

type Config struct {
	LogLevel      string        `yaml:"log_level"`
	CheckInterval time.Duration `yaml:"check_interval"`

	Monitor    MonitorConfig       `yaml:"monitor"`
	Thresholds ThresholdConfig     `yaml:"thresholds"`
	Coredump   CoredumpConfig      `yaml:"coredump"`
	External   ExternalConfig      `yaml:"external_healthcheck"`
	Release    MemoryReleaseConfig `yaml:"memory_release"`
}

type MonitorConfig struct {
	WindowSize            int           `yaml:"window_size"`
	SustainedRatio        float64       `yaml:"sustained_ratio"`
	MaxRecoveriesPerHour  int           `yaml:"max_recoveries_per_hour"`
	CooldownAfterRecovery time.Duration `yaml:"cooldown_after_recovery"`
	StopTimeout           time.Duration `yaml:"stop_timeout"`
	DropCachesMode        int           `yaml:"drop_caches_mode"`
}

type ThresholdConfig struct {
	PSICPUThreshold         float64       `yaml:"psi_cpu"`
	PSIMemoryThreshold      float64       `yaml:"psi_memory"`
	PSIIOThreshold          float64       `yaml:"psi_io"`
	IOWaitThreshold         float64       `yaml:"iowait"`
	MemoryUsageThreshold    float64       `yaml:"memory_usage"`
	CriticalMemoryThreshold float64       `yaml:"critical_memory"`
	MariaDBSwapThresholdMB  uint64        `yaml:"mariadb_swap_mb"`
	SwapHeadroom            float64       `yaml:"swap_headroom"`
	PageRateThreshold       float64       `yaml:"page_rate"`
	IOFreezeTimeout         time.Duration `yaml:"io_freeze_timeout"`
}

type CoredumpConfig struct {
	Enabled      bool          `yaml:"enabled"`
	OutputDir    string        `yaml:"output_dir"`
	Timeout      time.Duration `yaml:"timeout"`
	MaxCount     int           `yaml:"max_count"`
	MaxStorageGB float64       `yaml:"max_storage_gb"`
}

type ExternalConfig struct {
	Enabled    bool   `yaml:"enabled"`
	ServerName string `yaml:"server_name"`
	URL        string `yaml:"url"`
	Token      string `yaml:"token"`
}

type MemoryReleaseConfig struct {
	Enabled             bool          `yaml:"enabled"`
	MinFreeMB           uint64        `yaml:"min_free_mb"`
	Cooldown            time.Duration `yaml:"cooldown"`
	TcmallocThresholdMB int64         `yaml:"tcmalloc_threshold_mb"`
	MemHighThreshold    int           `yaml:"mem_high_threshold"`
	PSIMemoryThreshold  float64       `yaml:"psi_memory_threshold"`
	InnoDBBufferMinMB   uint64        `yaml:"innodb_buffer_min_mb"`
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
		LogLevel:      "WARN",
		CheckInterval: 5 * time.Second,

		Monitor: MonitorConfig{
			WindowSize:            12,
			SustainedRatio:        0.7,
			MaxRecoveriesPerHour:  3,
			CooldownAfterRecovery: 120 * time.Second,
			StopTimeout:           30 * time.Second,
			DropCachesMode:        1,
		},

		Thresholds: ThresholdConfig{
			PSICPUThreshold:         80.0,
			PSIMemoryThreshold:      60.0,
			PSIIOThreshold:          60.0,
			IOWaitThreshold:         50.0,
			MemoryUsageThreshold:    95.0,
			CriticalMemoryThreshold: 98.0,
			MariaDBSwapThresholdMB:  100,
			SwapHeadroom:            10.0,
			PageRateThreshold:       100000,
			IOFreezeTimeout:         5 * time.Second,
		},

		Coredump: CoredumpConfig{
			Enabled:      false,
			OutputDir:    "/var/lib/mariadb-monitor/coredumps",
			Timeout:      120 * time.Second,
			MaxCount:     3,
			MaxStorageGB: 15.0,
		},

		External: ExternalConfig{
			Enabled:    false,
			ServerName: "",
			URL:        "",
			Token:      "",
		},

		Release: MemoryReleaseConfig{
			Enabled:             true,
			MinFreeMB:           512,
			Cooldown:            5 * time.Minute,
			TcmallocThresholdMB: 2048,
			MemHighThreshold:    3,
			PSIMemoryThreshold:  20.0,
			InnoDBBufferMinMB:   256,
		},
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

	parseDurationAt(raw, &cfg.CheckInterval, "check_interval")
	parseDurationAt(raw, &cfg.Monitor.CooldownAfterRecovery, "monitor", "cooldown_after_recovery")
	parseDurationAt(raw, &cfg.Monitor.StopTimeout, "monitor", "stop_timeout")
	parseDurationAt(raw, &cfg.Thresholds.IOFreezeTimeout, "thresholds", "io_freeze_timeout")
	parseDurationAt(raw, &cfg.Coredump.Timeout, "coredump", "timeout")
	parseDurationAt(raw, &cfg.Release.Cooldown, "memory_release", "cooldown")

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
	if c.Monitor.WindowSize <= 0 {
		return fmt.Errorf("monitor.window_size must be > 0, got %d", c.Monitor.WindowSize)
	}
	if c.Monitor.SustainedRatio < 0 || c.Monitor.SustainedRatio > 1 {
		return fmt.Errorf("monitor.sustained_ratio must be between 0 and 1, got %.2f", c.Monitor.SustainedRatio)
	}
	if c.CheckInterval <= 0 {
		return fmt.Errorf("check_interval must be > 0")
	}
	if c.Monitor.MaxRecoveriesPerHour < 0 {
		return fmt.Errorf("monitor.max_recoveries_per_hour must be >= 0, got %d", c.Monitor.MaxRecoveriesPerHour)
	}
	if c.Monitor.DropCachesMode < 0 || c.Monitor.DropCachesMode > 3 {
		return fmt.Errorf("monitor.drop_caches_mode must be 0-3, got %d", c.Monitor.DropCachesMode)
	}
	if c.Coredump.Enabled && c.Coredump.OutputDir == "" {
		return fmt.Errorf("coredump.output_dir must be set when coredump.enabled is true")
	}
	if c.Coredump.MaxCount < 0 {
		return fmt.Errorf("coredump.max_count must be >= 0, got %d", c.Coredump.MaxCount)
	}
	if c.Release.MemHighThreshold < 1 {
		return fmt.Errorf("memory_release.mem_high_threshold must be >= 1, got %d", c.Release.MemHighThreshold)
	}
	if c.Release.MinFreeMB == 0 {
		return fmt.Errorf("memory_release.min_free_mb must be > 0")
	}
	if c.Release.InnoDBBufferMinMB == 0 {
		return fmt.Errorf("memory_release.innodb_buffer_min_mb must be > 0")
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

func parseDurationAt(raw map[string]interface{}, target *time.Duration, keys ...string) {
	m := raw
	for _, key := range keys[:len(keys)-1] {
		sub, ok := m[key]
		if !ok {
			return
		}
		nested, ok := sub.(map[string]interface{})
		if !ok {
			return
		}
		m = nested
	}
	v, ok := m[keys[len(keys)-1]]
	if !ok {
		return
	}
	if s, ok := v.(string); ok {
		if d, err := time.ParseDuration(s); err == nil {
			*target = d
		}
	}
}

func GenerateDefaultConfig() error {
	if err := os.MkdirAll(filepath.Dir(configFile), 0755); err != nil {
		return fmt.Errorf("create config dir: %w", err)
	}

	cfg := DefaultConfig()
	data, err := yaml.Marshal(cfg)
	if err != nil {
		return fmt.Errorf("marshal default config: %w", err)
	}

	content := "# MariaDB Monitor Configuration\n\n" + string(data)
	return os.WriteFile(configFile, []byte(content), 0644)
}
