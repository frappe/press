# Prometheus metrics for servers

Production Prometheus is at `https://monitor.frappe.cloud/prometheus`. A login is necessary,
so an agent cannot open a link itself.

An agent can get a fixed set of server metrics through a Press endpoint. Use the endpoint
first. If you need a PromQL query that the endpoint does not have, make a link (see
[Make a link](#make-a-link)). Give the link to the user, and ask for a screenshot.

## Get metrics through Press

`press.api.server.analytics` is the endpoint that the dashboard uses for its server charts.
It sends a fixed PromQL query to the monitor server and returns the result as JSON. Call it
with the `press-prod` profile of `frappectl`:

```bash
frappectl -s press-prod method call press.api.server.analytics \
	-f name=f927-mumbai.frappe.cloud -f query=cpu -f timezone=Asia/Kolkata \
	-f start=2026-11-04T05:30:00Z -f end=2026-11-04T11:30:00Z
```

Give `start` and `end` in UTC, in ISO format with a `Z`. The `timezone` changes only the
labels of the result. The result has this shape:

```json
{"datasets": [{"name": "iowait", "values": [3.1, 2.8]}], "labels": ["2026-11-04 11:00:00+05:30", "2026-11-04 11:01:00+05:30"]}
```

Each dataset has one value for each label. If Prometheus has no sample for a step, the value
is `null`.

### Queries

| `query` | Value | Dataset names |
|---|---|---|
| `cpu` | Percent of one core for each CPU mode. All modes added together equal 100 × the number of vCPUs. | `idle`, `iowait`, `user`, `system`, `steal`, `irq`, `softirq`, `nice` |
| `network` | Received bits per second. The endpoint has no query for sent traffic. | The network device, for example `ens5` |
| `iops` | Read and write operations per second for each disk. | `<device> read`, `<device> write` |
| `space` | Percent of the disk that is used. | The mount point |
| `loadavg` | Load average. | `Load Average 1`, `Load Average 5`, `Load Average 15` |
| `memory` | Used memory in bytes, without cache and buffers. | `Used` |
| `oom_kills` | OOM kills in each step. | `OOM Kills` |
| `database_uptime` | Percent of each step that MariaDB was up. | `Uptime` |
| `database_commands_count` | Number of each SQL command in each step. | The command, for example `select` |
| `database_connections` | Peak connected clients, and `max_connections`. | `Connected Clients`, `Max Connections` |
| `innodb_bp_size` | InnoDB buffer pool size in bytes. | `Buffer Pool Size` |
| `innodb_bp_size_of_total_ram` | Buffer pool size as a percent of RAM. | `Buffer Pool Size of Total Ram` |
| `innodb_bp_miss_percent` | Buffer pool reads that went to disk, as a fraction of all reads. | `Buffer Pool Miss Percentage` |
| `innodb_avg_row_lock_time` | Average row lock wait time. | `Avg Row Lock Time` |

The `database_*` and `innodb_*` queries work only for a database server, for example
`m123-mumbai.frappe.cloud`.

To get the CPU use as a percent, divide each mode by the total of all modes. The busy
percent is `100 - idle%`. If `idle` is near 100%, the network is near 0, and the disk
writes are low, the machine is idle.

### Notes

- The step is the scrape interval or longer. The endpoint picks the step to give about
  500 points at most. A 6 hour window gives 1 minute steps.
- `space` reads the data disk of an AWS EC2 server, and `/` for other providers. If a
  database server has a name that does not start with `m`, give `-f server_type="Database Server"`.
- The endpoint keeps each result in Redis for 10 minutes. If you call it again with the
  same arguments in that time, you get the same data.
- Do not call `press.api.server.prometheus_query` directly. It takes a Python function as
  an argument, so it fails over HTTP.

### Fetch several queries

This script saves each query for two servers as one JSON file. Change the servers and the
window:

```bash
out=$(mktemp -d)
for srv in f927-mumbai.frappe.cloud f860-mumbai.frappe.cloud; do
	for q in cpu iops space loadavg memory oom_kills network; do
		frappectl -s press-prod method call press.api.server.analytics \
			-f name=$srv -f query=$q -f timezone=Asia/Kolkata \
			-f start=2026-11-04T05:30:00Z -f end=2026-11-04T11:30:00Z \
			2>/dev/null > "$out/$srv-$q.json" &
	done
done
wait
echo "$out"
```

### Other server endpoints

These endpoints take the same `name`, `query`, `timezone`, `start` and `end` arguments.
They read the site logs, not Prometheus:

- `press.api.server.get_request_by_site`
- `press.api.server.get_background_job_by_site`
- `press.api.server.get_slow_logs_by_site`
- `press.api.server.get_slow_logs_by_query`

## URL format

The graph page reads its panels from the query string. Each panel `N` (from 0) uses these
parameters:

| Parameter | Value |
|---|---|
| `gN.expr` | The PromQL query. |
| `gN.tab` | `0` for the graph, `1` for the table. |
| `gN.range_input` | The width of the window: `1h`, `6h`, `1d`, `7d`. |
| `gN.end_input` | The end of the window, `YYYY-MM-DD HH:MM:SS`, in UTC. |
| `gN.moment_input` | The same value as `gN.end_input`. |

If "Use local time" is on, the page shows the times in the local time of the user. An
`end_input` of `06:30:00` UTC shows as `12:00:00` in IST.

## Make a link

URL-encode the query. Do not encode it by hand, because PromQL has `{`, `"`, `=~` and `|`.
Use this script. Change the label, the end time, and the queries:

```python
from urllib.parse import urlencode

labels = 'instance=~"u58-ashburn.*",job="node"'
end = "2026-09-24 06:30:00"  # UTC
queries = [
	f'sum(rate(node_network_receive_bytes_total{{{labels},device!~"lo|docker.*|veth.*|br-.*"}}[5m]))',
	f"rate(node_netstat_TcpExt_TCPOFOQueue{{{labels}}}[5m]) / rate(node_netstat_Tcp_InSegs{{{labels}}}[5m])",
]
params = {}
for n, expr in enumerate(queries):
	params |= {
		f"g{n}.expr": expr,
		f"g{n}.tab": "0",
		f"g{n}.range_input": "1d",
		f"g{n}.end_input": end,
		f"g{n}.moment_input": end,
	}
print("https://monitor.frappe.cloud/prometheus/graph?" + urlencode(params))
```

In an f-string, write `{{` and `}}` for the braces of the PromQL label set.

## Labels

node_exporter metrics have these labels:

- `instance`: the full server name, for example `u58-ashburn.frappe.cloud`.
- `job`: `node`.
- `cluster`: the cluster name, for example `Ashburn`.

Press uses `instance="<server>", job="node"` in `press/api/server.py`. If you do not know
the full server name, use a regex such as `instance=~"u58-ashburn.*"`. The legend of the
graph then shows the real label values.

## Useful queries for the network

| Question | Query |
|---|---|
| How fast does the server download? | `sum(rate(node_network_receive_bytes_total{…,device!~"lo\|docker.*\|veth.*\|br-.*"}[5m]))` |
| How fast does the server upload? | The same query with `node_network_transmit_bytes_total`. |
| Did the server lose packets on a download? | `rate(node_netstat_TcpExt_TCPOFOQueue{…}[5m]) / rate(node_netstat_Tcp_InSegs{…}[5m])` |
| Did the server lose packets on an upload? | `rate(node_netstat_Tcp_RetransSegs{…}[5m]) / rate(node_netstat_Tcp_OutSegs{…}[5m])` |

`Tcp_RetransSegs` counts only the packets that this server sends again. On a download, the
remote server sends the packets again, so this metric stays at zero. For a download, use the
out-of-order counter `TcpExt_TCPOFOQueue`.

When the traffic is low, a few out-of-order packets give a high ratio. Look at the
download speed at the same time before you decide that a spike is real loss.
