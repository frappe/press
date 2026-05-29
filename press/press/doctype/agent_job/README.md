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
