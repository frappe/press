# AgentJob

Every operation Press performs on a remote server — create site, install app, run backup, update bench — is executed by sending an HTTP request to the Agent (a Flask app running on each server). Each such request is tracked as an `AgentJob`.

## How it works

1. Code calls a method on the `Agent` class (`press/agent.py`), e.g. `Agent(server).new_site(...)`.
2. `Agent` creates an `AgentJob` record and POSTs to the Agent's HTTP API.
3. A scheduled job (`poll_pending_jobs`, runs every 5 seconds) polls the Agent for updates.
4. When the job finishes, `AgentJob` dispatches a callback to the originating doctype.

## Status lifecycle

```
Undelivered → Pending → Running → Success
                                 → Failure
                                 → Delivery Failure  (HTTP request never reached agent)
```

## Callbacks

Each doctype that creates an AgentJob defines a `process_*_job_update` function. `AgentJob.process_update()` calls the appropriate one based on `reference_doctype` and `job_type`. Example: a `SiteUpdate` job completion calls `process_site_update_job_update`.

## Key fields

| Field | Description |
|-------|-------------|
| `server` / `server_type` | Which server the job runs on |
| `job_type` | The type of operation (matches `Agent Job Type` fixture) |
| `reference_doctype` / `reference_name` | The document that owns this job |
| `request_data` | JSON payload sent to the Agent |
| `output` / `traceback` | Result from the Agent |

## Timezones

The fields of one Agent Job are not all in the same timezone.

| Field | Timezone | Set by |
|-------|----------|--------|
| `creation`, `modified` | System timezone (Asia/Kolkata on Frappe Cloud) | Frappe |
| `next_retry_at` | System timezone | `get_next_retry_at`, from `now_datetime()` |
| `start`, `end` | **UTC** | The agent, with `datetime.now()` on the server. `update_job` stores the value without a change. |
| `start`, `end` of each Agent Job Step | **UTC** | The agent. `update_steps` stores the value without a change. |
| `duration` | No timezone | The agent, as `end - start` |

Press converts `start` and `end` to the system timezone only for the dashboard: in `AgentJob.get_doc` and in `get_list` (through `update_query_result_status_timestamps`). Other reads get the UTC value. This includes the Desk form, `frappe.get_all`, `frappe.qb`, SQL, and reports. The Desk form therefore shows `start` and `end` 5.5 hours before `creation`.

Do not compare `start` or `end` with `creation`, `now_datetime()`, or a period in system time. Convert one side first:

- To filter on `end`, convert the period to UTC. See `Period.in_utc` in the Build Server Stats report.
- To show or bucket `end`, use `convert_utc_to_system_timezone(end).replace(tzinfo=None)`.

`end - start` is correct, because both values are in UTC.

The value is UTC only because every server runs in UTC. A server with a different clock timezone gives wrong `start` and `end` values.
