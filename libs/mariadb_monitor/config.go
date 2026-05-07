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
	WindowSize          int     `yaml:"window_size"`
	SustainedRatio      float64 `yaml:"sustained_ratio"`
	StuckQueryThreshold int     `yaml:"stuck_query_threshold"`
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
	Cooldown     time.Duration `yaml:"cooldown"`
	MaxCount     int           `yaml:"max_count"`
	MaxStorageGB float64       `yaml:"max_storage_gb"`
}

<<<<<<< HEAD
	CoredumpEnabled            bool          `yaml:"coredump_enabled"`
	CoredumpOutputDir          string        `yaml:"coredump_output_dir"`
	CoredumpTimeout            time.Duration `yaml:"coredump_timeout"`
	CoredumpMaxCount           int           `yaml:"coredump_max_count"`
	CoredumpOnUnhealthy        bool          `yaml:"coredump_on_unhealthy"`
	CoredumpOnFrequentTriggers bool          `yaml:"coredump_on_frequent_triggers"`
	CoredumpFrequentThreshold  int           `yaml:"coredump_frequent_threshold"`
<<<<<<< HEAD
	CoredumpPreemptive         bool          `yaml:"coredump_preemptive"`
	CoredumpPreemptiveAfter    int           `yaml:"coredump_preemptive_after"`
	CoredumpPreemptiveWindow   time.Duration `yaml:"coredump_preemptive_window"`
	CoredumpCooldown           time.Duration `yaml:"coredump_cooldown"`
=======

	ExternalHealthCheckEnabled bool   `yaml:"external_healthcheck_enabled"`
	ServerName                 string `yaml:"server_name"`
	ExternalHealthCheckURL     string `yaml:"external_health_check_url"`
	ExternalHealthCheckToken   string `yaml:"external_health_check_token"`
>>>>>>> 73ddc0842 (feat(mariadb-monitor): Ask press to check db health via app server)
=======
type ExternalConfig struct {
	Enabled    bool   `yaml:"enabled"`
	ServerName string `yaml:"server_name"`
	URL        string `yaml:"url"`
	Token      string `yaml:"token"`
}

type MemoryReleaseConfig struct {
<<<<<<< HEAD
	Enabled             bool          `yaml:"enabled"`
	MinFreeMB           uint64        `yaml:"min_free_mb"`
	Cooldown            time.Duration `yaml:"cooldown"`
	TcmallocThresholdMB int64         `yaml:"tcmalloc_threshold_mb"`
	MemHighThreshold    int           `yaml:"mem_high_threshold"`
	PSIMemoryThreshold  float64       `yaml:"psi_memory_threshold"`
	InnoDBBufferMinMB   uint64        `yaml:"innodb_buffer_min_mb"`
<<<<<<< HEAD
>>>>>>> d97e09880 (feat(mariadb-monitor): Add auto-trim memory usage)
=======
	SwapMinMB           uint64        `yaml:"swap_min_mb"`
>>>>>>> e4c5b14e7 (feat(mariadb-monitor): Dont take action if db using less than 50MB swap)
=======
	Enabled                 bool          `yaml:"enabled"`
	MinFreeMB               uint64        `yaml:"min_free_mb"`
	Cooldown                time.Duration `yaml:"cooldown"`
	TcmallocThresholdMB     int64         `yaml:"tcmalloc_threshold_mb"`
	MemHighThreshold        int           `yaml:"mem_high_threshold"`
	PSIMemoryThreshold      float64       `yaml:"psi_memory_threshold"`
	InnoDBBufferMinMB       uint64        `yaml:"innodb_buffer_min_mb"`
	SwapReclaimMinMB        uint64        `yaml:"swap_reclaim_min_mb"`
	SwapReclaimFreeRAMRatio float64       `yaml:"swap_reclaim_free_ram_ratio"`
<<<<<<< HEAD
>>>>>>> 43fb17b91 (feat(mariadb-monitor): If stuck queries piled up, assume db unhealthy)
=======

	// KillableProcesses is a list of process names that may be SIGKILLed
	// under urgent memory pressure. Use for non-essential workloads only.
	// mariadbd/mysqld are always excluded.
	KillableProcesses []string `yaml:"killable_processes"`
>>>>>>> 0fb344429 (feat(mariadb-monitor): Tune auto-release memory and recovery of buffer)
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

<<<<<<< HEAD
		CoredumpEnabled:            false,
		CoredumpOutputDir:          "/var/lib/mariadb-monitor/coredumps",
		CoredumpTimeout:            120 * time.Second,
		CoredumpMaxCount:           3,
		CoredumpOnUnhealthy:        true,
		CoredumpOnFrequentTriggers: true,
		CoredumpFrequentThreshold:  3,
<<<<<<< HEAD
		CoredumpPreemptive:         true,
		CoredumpPreemptiveAfter:    6,
		CoredumpPreemptiveWindow:   5 * time.Minute,
		CoredumpCooldown:           5 * time.Minute,
=======

		ExternalHealthCheckEnabled: false,
		ServerName:                 "",
		ExternalHealthCheckURL:     "",
		ExternalHealthCheckToken:   "",
>>>>>>> 73ddc0842 (feat(mariadb-monitor): Ask press to check db health via app server)
=======
		Monitor: MonitorConfig{
			WindowSize:          12,
			SustainedRatio:      0.7,
			StuckQueryThreshold: 30,
		},

		Thresholds: ThresholdConfig{
			PSICPUThreshold:      80.0,
			PSIMemoryThreshold:   60.0,
			PSIIOThreshold:       60.0,
			IOWaitThreshold:      50.0,
			MemoryUsageThreshold: 95.0,
			// 99.0: on hosts with a cgroup memory.max limit the kernel
			// throttles well before user-space reaches 99.7%.
			CriticalMemoryThreshold: 99.0,
			MariaDBSwapThresholdMB:  100,
			SwapHeadroom:            10.0,
			PageRateThreshold:       100000,
			IOFreezeTimeout:         5 * time.Second,
		},

		Coredump: CoredumpConfig{
			Enabled:      false,
			OutputDir:    "/var/lib/mariadb-monitor/coredumps",
			Timeout:      120 * time.Second,
			Cooldown:     1 * time.Hour,
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
			Enabled: true,
			// ~20% of a typical 8 GiB host.
			MinFreeMB: 1536,
			// Must be > minBufferRestoreGracePeriod to avoid thrashing.
			Cooldown:            3 * time.Minute,
			TcmallocThresholdMB: 256,
			// 6 ticks × 5s = 30s of sustained cgroup pressure before acting.
			MemHighThreshold:        6,
			PSIMemoryThreshold:      20.0,
			InnoDBBufferMinMB:       256,
			SwapReclaimMinMB:        150,
			SwapReclaimFreeRAMRatio: 1.5,
			KillableProcesses:       []string{},
		},
>>>>>>> d97e09880 (feat(mariadb-monitor): Add auto-trim memory usage)
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

<<<<<<< HEAD
	parseDuration(raw, "check_interval", &cfg.CheckInterval)
	parseDuration(raw, "cooldown_after_recovery", &cfg.CooldownAfterRecovery)
	parseDuration(raw, "stop_timeout", &cfg.StopTimeout)
	parseDuration(raw, "io_freeze_timeout", &cfg.IOFreezeTimeout)
	parseDuration(raw, "coredump_timeout", &cfg.CoredumpTimeout)
	parseDuration(raw, "coredump_cooldown", &cfg.CoredumpCooldown)
	parseDuration(raw, "coredump_preemptive_window", &cfg.CoredumpPreemptiveWindow)
=======
	parseDurationAt(raw, &cfg.CheckInterval, "check_interval")
	parseDurationAt(raw, &cfg.Thresholds.IOFreezeTimeout, "thresholds", "io_freeze_timeout")
	parseDurationAt(raw, &cfg.Coredump.Timeout, "coredump", "timeout")
	parseDurationAt(raw, &cfg.Coredump.Cooldown, "coredump", "cooldown")
	parseDurationAt(raw, &cfg.Release.Cooldown, "memory_release", "cooldown")
>>>>>>> d97e09880 (feat(mariadb-monitor): Add auto-trim memory usage)

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
	if c.Monitor.StuckQueryThreshold < 1 {
		return fmt.Errorf("monitor.stuck_query_threshold must be >= 1, got %d", c.Monitor.StuckQueryThreshold)
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
<<<<<<< HEAD
	if c.CoredumpPreemptiveAfter < 1 {
		return fmt.Errorf("coredump_preemptive_after must be >= 1, got %d", c.CoredumpPreemptiveAfter)
=======
	if c.Release.SwapReclaimFreeRAMRatio <= 0 {
		return fmt.Errorf("memory_release.swap_reclaim_free_ram_ratio must be > 0, got %.2f", c.Release.SwapReclaimFreeRAMRatio)
	}
	if c.Release.Cooldown < minBufferRestoreGracePeriod {
		return fmt.Errorf("memory_release.cooldown (%s) must be >= %s to avoid shrink-restore-shrink thrashing",
			c.Release.Cooldown, minBufferRestoreGracePeriod)
	}
	for _, name := range c.Release.KillableProcesses {
		if isProtectedProcessName(name) {
			return fmt.Errorf("memory_release.killable_processes must not include %q (protected)", name)
		}
>>>>>>> 0fb344429 (feat(mariadb-monitor): Tune auto-release memory and recovery of buffer)
	}
	return nil
}

// isProtectedProcessName returns true for names that must never be killable
// via the killable_processes list.
func isProtectedProcessName(name string) bool {
	switch strings.ToLower(strings.TrimSpace(name)) {
	case "", "mariadbd", "mysqld", "init", "systemd", "kthreadd",
		"sshd", "mariadb-monitor":
		return true
	}
	return false
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
<<<<<<< HEAD
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
coredump_preemptive: %t
coredump_preemptive_after: %d
coredump_preemptive_window: %s
coredump_cooldown: %s
`,
		cfg.CoredumpEnabled,
		cfg.CoredumpOutputDir,
		cfg.CoredumpTimeout,
		cfg.CoredumpMaxCount,
		cfg.CoredumpOnUnhealthy,
		cfg.CoredumpOnFrequentTriggers,
		cfg.CoredumpFrequentThreshold,
		cfg.CoredumpPreemptive,
		cfg.CoredumpPreemptiveAfter,
		cfg.CoredumpPreemptiveWindow,
		cfg.CoredumpCooldown,
	)

	content += fmt.Sprintf(`
# External health check (optional, disabled by default). When local check
# passes, this endpoint is queried for a second opinion. If the external API
# reports the app server as healthy but the db server as unhealthy, recovery
# proceeds. Any non-200 response, transport error, or timeout is ignored.
external_healthcheck_enabled: %t
server_name: %q
external_health_check_url: %q
external_health_check_token: %q
`,
		cfg.ExternalHealthCheckEnabled,
		cfg.ServerName,
		cfg.ExternalHealthCheckURL,
		cfg.ExternalHealthCheckToken,
	)
=======
	data, err := yaml.Marshal(cfg)
	if err != nil {
		return fmt.Errorf("marshal default config: %w", err)
	}
>>>>>>> d97e09880 (feat(mariadb-monitor): Add auto-trim memory usage)

	content := "# MariaDB Monitor Configuration\n\n" + string(data)
	return os.WriteFile(configFile, []byte(content), 0644)
}
