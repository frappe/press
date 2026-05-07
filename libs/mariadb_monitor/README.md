# MariaDB Monitor

Watch mariadb health and system metrics. Tries to reduce memory usage of system or recover system in case of stall.

## Install

```sh
sudo ./mariadb_monitor install
```

Requires `/root/.my.cnf`:

```ini
[client]
user=root
password=your_secure_password
socket=/var/run/mysqld/mysqld.sock
```

## Commands

| Command | Description |
|---|---|
| `install` | Install binary, config, and systemd service |
| `uninstall` | Remove binary and service (keeps config) |
| `run` | Run in foreground, log to stdout |
| `help` | Show help |

## Config

Path: `/etc/mariadb-monitor/config.yaml`

### General

| Key | Default | Description |
|---|---|---|
| `log_level` | `WARN` | DEBUG, INFO, WARN, ERROR |
| `check_interval` | `5s` | Sample interval |

### Monitor

| Key | Default | Description |
|---|---|---|
| `window_size` | `12` | Samples kept (12 * 5s = 1 min) |
| `sustained_ratio` | `0.7` | Fraction of samples over threshold to trigger |
| `max_recoveries_per_hour` | `3` | Max restarts per rolling hour |
| `cooldown_after_recovery` | `2m` | Pause after restart |
| `stuck_query_threshold` | `30` | Stuck queries (`Opening tables` / `Killed`) to trigger |

Recovery: SIGKILL mariadbd, poll until dead, clear failed state, start. Drops page cache before restart. If SIGKILL fails or DB never becomes reachable, hard-reboots via sysrq.

### Thresholds

| Key | Default | Description |
|---|---|---|
| `psi_cpu` | `80` | CPU pressure (avg60 some) |
| `psi_memory` | `60` | Memory pressure (avg60 full) |
| `psi_io` | `60` | IO pressure (avg60 full) |
| `iowait` | `50` | % CPU waiting for IO |
| `memory_usage` | `95` | % system memory used |
| `critical_memory` | `98` | % memory used; bypasses window, fires immediately |
| `mariadb_swap_mb` | `100` | Max swap used by mariadb cgroup |
| `swap_headroom` | `10` | Free swap % threshold for predictive check |
| `page_rate` | `100000` | Pages/s (in + out) |
| `io_freeze_timeout` | `5s` | Max time for test write; longer = frozen disk |

### Memory Release

| Key | Default | Description |
|---|---|---|
| `enabled` | `true` | Enable soft relief |
| `min_free_mb` | `512` | Target free memory |
| `cooldown` | `5m` | Min time between relief attempts |
| `tcmalloc_threshold_mb` | `2048` | Min tcmalloc heap free before releasing |
| `mem_high_threshold` | `3` | Consecutive `memory.high` events to trigger |
| `psi_memory_threshold` | `20` | PSI memory threshold for relief |
| `innodb_buffer_min_mb` | `256` | Min InnoDB buffer pool size |
| `swap_reclaim_min_mb` | `150` | Min mariadb swap to trigger swap reclaim; `0` disables |
| `swap_reclaim_free_ram_ratio` | `1.5` | Free RAM must be >= this * total swap to reclaim |

Swap reclaim guards: swap > `swap_reclaim_min_mb`, free RAM >= `swap_reclaim_free_ram_ratio` * swap, PSI memory < `psi_memory_threshold`.

### Coredump (default: off)

| Key | Default | Description |
|---|---|---|
| `enabled` | `false` | `gcore` before restart |
| `output_dir` | `/var/lib/mariadb-monitor/coredumps` | |
| `timeout` | `120s` | |
| `max_count` | `3` | |
| `max_storage_gb` | `15` | |

### External Healthcheck (default: off)

| Key | Default | Description |
|---|---|---|
| `enabled` | `false` | |
| `server_name` | `""` | |
| `url` | `""` | POST endpoint |
| `token` | `""` | Auth token |

## Restart Conditions

Restart happens only when **both** are true:

1. At least one trigger fires (sustained PSI, memory, IO freeze, swap, cgroup pressure, predictive exhaustion, machine frozen, or stuck queries >= threshold)
2. MariaDB is unreachable, has stuck query pile-up, or external healthcheck reports unhealthy

## Logs

`/var/log/mariadb-monitor/monitor.log`