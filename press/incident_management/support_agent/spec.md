# Support Agent Investigation Spec

## Goal

Build a site-scoped support investigation workflow in Press that helps support agents inspect Frappe Cloud issues using only read-only, allowlisted platform facts.

The only required input is a site name or site domain.

## Non-Goals

- Do not query the hosted site's database.
- Do not read customer documents, users, emails, invoices, tickets, or billing records.
- Do not expose raw logs, raw request payloads, secrets, tokens, cookies, or full stack traces with local variable frames to the report generator. Redacted exception message lines (last line of a traceback) are permitted and treated as structured data.
- Do not allow the report generator to call generic Press document APIs or run arbitrary queries.
- Do not perform remediation actions such as restarts, retries, migrations, backups, or plan changes.

## User Flow

1. A support user starts an investigation for a site.
2. Press creates a `Support Agent Investigation` document in `Queued` state.
3. Press enqueues the document's `run` method on the long queue.
4. The runner collects only allowlisted platform facts for the site.
5. Press redacts the complete payload before storing or reporting on it.
6. The report generator creates a summary, likely cause, evidence, timeline, confidence, and next steps.
7. The investigation document is marked `Completed` or `Failed`.

## DocType

`Support Agent Investigation`

Important fields:

- `site`: Link to `Site`.
- `status`: `Queued`, `Running`, `Completed`, `Failed`.
- `requested_by`: User who created the investigation.
- `started_at`, `completed_at`: Execution timestamps.
- `summary`: Short support-facing summary.
- `likely_cause`: Top likely cause.
- `recommended_next_steps`: Safe follow-up steps, newline-separated.
- `confidence`: `Low`, `Medium`, `High`.
- `evidence_json`: Redacted evidence strings.
- `timeline_json`: Redacted timeline items.
- `errors_json`: Aggregated redacted error summary.
- `payload_json`: Full redacted structured payload.
- `failure_reason`: Redacted failure reason if the runner fails.
- `redaction_version`: Version string of the redactor applied to this record.
- `llm_model`: Reserved for a future LLM integration; currently unused.

## Public API

The feature exposes three narrow whitelisted entrypoints.

Module-level functions (not controller methods):

- `create_investigation(site: str, run_now: bool = True) -> str`
- `get_investigation(name: str) -> dict`

Controller method:

- `SupportAgentInvestigation.start()`

`get_investigation` returns: `name`, `site`, `status`, `summary`, `likely_cause`, `recommended_next_steps`, `confidence`, `evidence`, `timeline`, `errors`, `failure_reason`, `started_at`, `completed_at`.

All entrypoints validate site access before returning data or starting work.

## Access Model

A site can be investigated if:

- the caller is a system user, or
- the caller has `System Manager`, or
- the caller has accepted support access for the target `Site`.

Site domains are resolved to their owning site before access validation.

## Collectors

Collectors return structured facts only. They intentionally avoid raw logs, raw agent output, request data, traceback, site database access, and customer-owned records.

Current collectors:

- **Site health**: lifecycle status, bench/server/cluster links, setup and monitoring flags, usage percentages.
- **Bench health**: bench status, worker configuration, deploy candidate/build, queue-related flags (`merge_all_rq_queues`, `merge_default_and_short_rq_queues`, `use_rq_workerpool`), and failure markers (`last_inplace_update_failed`, `resetting_bench`).
- **App versions**: bench app, source, release, hash. Up to all apps on the bench, ordered by index.
- **Deployment timeline**: 5 most recent `Site Update` records — safe status/timing fields only (`status`, `deploy_type`, `scheduled_time`, `update_start`, `update_end`, `update_duration`, `backup_type`, `skipped_backups`, `skipped_failing_patches`).
- **Background jobs**: up to 10 recent `Agent Job` records in the last 24 hours, counts by status, excluding output/request/traceback fields.
- **Backups**: 5 most recent backup status and safe size/status metadata, excluding URLs.
- **Domains**: total count, counts by status, and per-record `status`/`dns_type`/`redirect_to_primary` — no domain names or DNS response bodies.
- **Platform incidents**: up to 5 active incident records matching the site's server or cluster (or-filter), excluding resolved/auto-resolved/press-resolved incidents.
- **Error summary**: 24-hour window, aggregated failed job counts by job type, up to 10 recent failed jobs listed, excluding raw output and stack traces.
- **Bench process status**: Supervisor process list for the site's bench. Each entry records the process name, status, and message. Processes not in `Running` or `Starting` state are collected as `stopped_processes`. Collected via `Bench.supervisorctl_status()` — an agent call to the app server.
- **Web error log**: Recent ERROR and CRITICAL entries from `web.error.log` on the site's app server. Only the gunicorn-level description and the final exception message line are captured — not full stack frames with local variables. All entries are redacted before being stored. Collects at most 10 error blocks from the last 500 log lines.
- **Site performance summary**: Up to 20 slowest endpoints from Elasticsearch over the last 24 hours. Each endpoint includes average and peak duration, a `spike_detected` flag (peak ≥ 3× mean and peak > 2 s), and an `is_custom` flag indicating whether the endpoint belongs to a non-Frappe app. App origin is determined by checking `repository_owner` on the AppSource record — any owner other than `frappe` is treated as custom. Also includes a `has_custom_apps` flag indicating whether any non-Frappe apps are installed on the bench.
- **Site uptime**: Probe result from the Prometheus blackbox exporter at the incident time — `probe_success` (up/down) and `probe_http_status_code`. Collected only when a monitor server is configured.
- **Server disk usage**: Fullest filesystem percentage on the app and database servers (instant query at the incident time). `full` is flagged at ≥ 98%.
- **Database iowait**: Percent of CPU spent waiting on disk. Used to qualify IOPS — disk I/O is only treated as a bottleneck when iowait is also elevated (≥ 20%).
- **Monitor health**: Whether the monitor server is reporting its own node-exporter metrics. Used to tell "both servers are down" apart from "the monitor is down" when neither app nor DB server reports metrics.
- **Recent slow endpoints**: A second slow-endpoint query over the last hour (in addition to 24 h), so a problem happening *right now* is surfaced separately from historical averages.

## Time Anchoring

Every investigation is anchored to an `incident_time` — a moment when the site was facing the
issue (not necessarily when it started). It defaults to now and can be set when creating the
investigation, to diagnose a past incident. All time-windowed collectors (server metrics, uptime
probe, slow endpoints, background jobs, error summary) look back from this point rather than from
the wall clock.

## Investigation Flow

```
incident_time (or now)
   |  anchor all windows back from here
   v
collect facts -> redact PII -> evaluate signals
   |
   +- metrics -- both servers silent --+- monitor up     -> BOTH SERVERS DOWN ......... High
   |                                   +- monitor silent -> MONITOR DOWN (caveat only)
   |          \- one server silent ----------------------> THAT SERVER DOWN ......... High
   |
   +- disk >= 98% --+- DB  -> DB DISK FULL -> 500s ........................ High
   |                \- app -> APP DISK FULL -> assorted errors ............ High
   |
   +- IOPS spike ---+- iowait high   -> DB I/O-BOUND ...................... cause
   |                \- iowait normal -> throughput only .................. not a cause
   |
   +- incident -----+- own server   -> likely cause ...................... High
   |                \- cluster only -> unlikely unless cluster-wide
   |
   \- slow custom endpoint in last 1h -> LIVE PROBLEM ................... High
              |
              v
   >= 2 causes? --yes--> uptime graph: earliest signal = CAUSE, later = SYMPTOMS
              \--no---> single likely_cause
              |
              v
   report: cause / next_steps / confidence --> (optional) AI analysis
```

## Performance Investigation

Performance tickets require a structured escalation path through platform-observable signals before conclusions can be drawn.

### Investigation order

1. **Check incidents first.** An active platform incident on the site's server or cluster is the most likely explanation for sudden slowness. The incident collector already covers this.

2. **Check server charts for spikes.** Collect recent CPU, memory, and disk-I/O time-series data from the site's app server and database server. A spike coinciding with the reported slowness window is meaningful signal.

3. **If a spike is observed, check server advanced analytics.** Advanced analytics break down resource usage across all tenants sharing the server. This is the mechanism for ruling in or ruling out a noisy neighbor.

### Noisy neighbor context

**App server — memory:** Bench containers on shared app servers run with memory limits enforced. Memory pressure from one tenant cannot directly starve another. Memory is not a useful noisy-neighbor signal on app servers.

**App server — CPU:** Bench containers on shared app servers have no CPU limits. A CPU-heavy tenant can crowd out others. If app-server CPU charts show a spike and the site's own usage does not explain it, advanced analytics should be checked for other benches on the same server consuming the burst.

**Database server:** MariaDB instances on shared database servers have no container-level CPU or memory isolation. There is currently no platform-side solution to noisy-neighbor problems on shared database servers. If DB-server CPU or I/O charts show a spike, advanced analytics can identify the contributing tenant, but remediation requires a manual decision (e.g. moving the site or the noisy tenant to a dedicated server).

### Collector additions needed

- **App server metrics**: recent CPU, memory time-series from the site's `Server`. Flag any spike above a threshold in the investigation window.
- **Database server metrics**: recent CPU, disk-I/O time-series from the site's `DatabaseServer`. Flag spikes similarly.
- **Server advanced analytics** (conditional): only collected when a spike is detected on either server. Returns per-bench or per-site resource breakdown for the spike window, excluding tenant names — counts and relative percentages only.

### Report signals to add

- Spike on app-server CPU with no matching incident → suggest checking advanced analytics for noisy neighbor.
- Spike on database-server CPU or I/O → note that shared DB servers have no isolation; advanced analytics can identify the tenant but there is no automatic fix.
- No spike on either server during the reported window → platform infrastructure is not the cause; redirect investigation to app-level slow queries or the customer's workload.

## Error Code Investigation Patterns

The investigation report should vary its signals and next steps based on the class of error the support ticket describes. The agent cannot read site-level logs directly; it works from platform-observable facts and directs the agent to the right place for the rest.

### 504 Gateway Timeout / Site Slow

**What it means:** Web workers on the site are all busy; requests queue and time out.

**Platform-side checks (what the agent can see):**

- Site CPU and database usage percentages — already collected in site health.
- App-server and database-server CPU charts for spikes in the reported window.
- Active platform incidents on the server or cluster.
- Recent failed or long-running Agent Jobs.
- Bench worker configuration (`background_workers`, `gunicorn_workers`, `auto_scale_workers`).

**Report signals to surface:**

- If a CPU spike is visible on the app server and no incident explains it, flag potential noisy neighbor (see Performance Investigation — no CPU limits on bench containers).
- If a CPU spike is visible on the database server, flag it with the caveat that shared DB servers have no isolation and the only remediation is moving tenants.
- If neither server shows a spike, check site analytics for slow endpoints. The investigation collects the 20 slowest endpoints by average duration over 24 hours. Each endpoint has `spike_detected` (peak ≥ 3× mean and peak > 2 s) and `is_custom` (endpoint belongs to a non-Frappe app based on `repository_owner` of the AppSource).
  - If a slow endpoint is `is_custom: true`, the cause is custom code, not infrastructure. Recommend Frappe Recorder to profile the endpoint.
  - If an endpoint is `spike_detected: true` with a low average, the slowness is triggered by a specific document type or operation — Recorder should capture the request in context.
  - If all slow endpoints are Frappe core (`is_custom: false`), recommend Recorder and mention common patterns: `frappe.desk.query_report.run` and `frappe.desk.reportview.get` (list/report views with missing indexes), `run_doc_method` (custom controller methods).
- Disable Recorder immediately after profiling to avoid further degradation.

---

### 502 Bad Gateway

**What it means:** Web worker processes have crashed completely, not just busy.

**Platform-side checks (what the agent can see):**

- Bench status (non-Active bench is a direct cause).
- Recent deployments — a failed site update can leave workers in a broken state.
- Recent Agent Jobs — a failed restart or migrate job is evidence.
- Active platform incidents.

**Report signals to surface:**

- If bench is not Active or a recent deployment ended in `Fatal` or `Cancelled`, that is the likely cause. A deployment in `Failure` state is transient — a recovery job is being created; check back shortly.
- The investigation collects the supervisor process list for the bench. If the gunicorn web process (`*-frappe-web`) is not `Running`, that is a direct cause of 502 errors — surface it immediately and recommend checking `web.error.log` and recent deployments before restarting.
- If no deployment or incident explains it, the crash may be from an application exception. The investigation automatically collects recent ERROR/CRITICAL entries from `web.error.log`. If those entries show a database connectivity error, flag it as the cause. If they show CRITICAL entries (worker timeouts or crashes), surface that. Only direct the support agent to open the log manually if no entries were collected or the log was unavailable.
- Do not recommend `bench restart` as a first step before log review; a restart without diagnosis will recur.

---

### 500 Internal Server Error

**What it means:** The application raised an unhandled exception. Almost always app-level, not infrastructure.

**Two presentation modes:**

- **Frappe shows the traceback in the UI.** The customer or support agent can read it directly. There is little for the investigation agent to add here — the error is self-describing.
- **Werkzeug blank error page.** The traceback is not surfaced to the UI. This requires reading `web.error.log` via Bench Group → Sites → View Logs. The agent should direct the support agent there.

**Platform-side checks (what the agent can see):**

- Bench status and recent deployments — a failed patch during a site update can put the app in a broken state.
- Recent failed Agent Jobs (especially migrate or install-app jobs).
- Database server health — a "can't connect to database server" traceback looks like a 500 but is infrastructure.

**Report signals to surface:**

- If a recent site update is in Failure/Fatal state, that is the likely cause. The update may have left a partially applied migration or a failing patch.
- If the error is intermittent (occasional pop-up rather than every request), it is likely a background job failure — direct to Scheduled Job Log and Error Log first, then `worker.err.log`.
- The investigation automatically collects recent ERROR entries from `web.error.log`. If entries show database connectivity failures (e.g. `OperationalError: Can't connect`), surface that as the cause. If entries show import errors, surface the broken-state cause. This covers the Werkzeug blank page case without requiring the support agent to open the log manually.
- If `web.error.log` was unavailable or returned no errors but 500s are still reported, direct to `web.error.log` via Bench Group → Sites → View Logs as a fallback.

## Redaction

**Redaction is the primary privacy gate.** No data reaches the LLM, or is persisted to the investigation record, until it has passed through `redact`. The goal is to ensure no personally identifiable information (PII) is ever sent to an external model.

All collected payloads pass through `redact` before report generation and persistence.

The redactor removes:

- email addresses,
- phone numbers,
- IPv4 addresses,
- bearer tokens,
- authorization headers,
- common secret assignments (`api_key`, `access_key`, `secret`, `token`, `password`, `authorization`, `cookie` in `key=value` patterns),
- values under secret-like keys such as `password`, `secret`, `token`, `api_key`, `apikey`, and `cookie`.

Redaction version: `support-agent-redaction-v1`.

The redaction step must be maintained and extended as new collectors are added. Any new field that could carry PII — user names, site domains, customer-entered text — must either be excluded at the collector level or stripped by the redactor. When in doubt, exclude at the collector; redaction is a safety net, not the first line of defense.

## Report Generation

The current implementation is deterministic and rule-based. It does not call an LLM yet.

It flags signals such as:

- inactive/broken/suspended site status,
- non-active bench status,
- fatally failed or cancelled site updates (`Fatal`, `Cancelled` are terminal failure states; `Failure` is transient — a recovery job is created shortly after and the update moves to `Recovering` → `Recovered` or `Fatal`),
- recent failed agent jobs,
- critical disk/database/CPU usage (≥120% flagged as a cause; ≥90% flagged as evidence),
- broken site domains,
- latest failed backup,
- incidents on the site's **own server** (incidents elsewhere in the same cluster are noted but treated as unlikely causes unless the whole cluster is down),
- a server reporting **no metrics** (likely down); if *both* servers are silent, the monitor's own metrics decide between "both servers down" and "monitor down",
- **disk full** (≥ 98%) on the database server (commonly a 500) or the app server (assorted errors, not always 500),
- a database **IOPS** spike — but only raised as a cause when CPU **iowait** is also elevated; otherwise it is just high throughput,
- **slow custom-app endpoints in the last hour**, treated as the live cause with high confidence.

When more than one cause is found, the report adds a step directing the agent to the uptime graph to find which signal started earliest — the earliest signal is the cause; later ones are likely symptoms (a slow query drives DB CPU up, not the reverse).

Confidence is `High` if any blocking signal is present (non-Active site or bench, fatal deployment, failed jobs, own-server incident, a single server down, disk full, or live slow custom endpoints), `Medium` if other causes were found, and `Low` if no causes were found.

The report generator returns:

- `summary`,
- `likely_cause`,
- `recommended_next_steps`,
- `confidence`,
- `evidence`,
- `timeline`.

## AI Analysis

After a deterministic investigation completes, a support agent can trigger an AI analysis pass by clicking **Get AI Analysis** on the investigation form. The button calls `SupportAgentInvestigation.run_llm_analysis()`.

### What is sent

The model receives `payload_json` (already redacted) plus the deterministic report fields (`summary`, `likely_cause`, `confidence`, `evidence`, `recommended_next_steps`). Before the payload is sent, all platform identifiers are stripped from the `site` and `bench` sections — the model only needs structured metrics and status flags, not names or infrastructure links.

Fields stripped from `site`: `name`, `bench`, `server`, `database_server`, `cluster`, `group`.

Fields stripped from `bench`: `name`, `server`, `database_server`, `cluster`, `candidate`, `build`.

No raw logs, no PII, and no customer documents are ever included. The redaction pipeline is the primary gate; the site name strip is an additional anonymizing step.

### Privacy boundary

```text
collect_site_context()
  -> redact()                    ← strips PII (emails, IPs, tokens, secrets)
  -> payload_json stored on doc
  -> run_llm_analysis()
       -> _anonymise()           ← removes site.name
       -> Claude API (claude-sonnet-4-6, HTTPS)
       -> llm_response stored on doc
```

No payload reaches the model unless it has passed through both `redact()` and `_anonymise()`. This is a hard requirement.

### Configuration

Set **Anthropic API Key** under Press Settings → Monitoring. The key is stored encrypted and retrieved at call time via `get_decrypted_password`.

### Model and output

Model: `claude-sonnet-4-6` (1 024 max output tokens).

The model is asked to:
1. Confirm or refine the deterministic likely cause.
2. Surface any signals the rule-based analysis missed.
3. Suggest refined next steps for the support agent.

The response is stored verbatim in `llm_response` on the investigation record. It is not written back to `likely_cause` or `recommended_next_steps` — the deterministic report fields remain unchanged so they can be compared side-by-side.

The `llm_model` field is updated to the model ID used when the analysis runs.

## Verification

Expected checks for this feature:

```bash
ruff check "press/incident_management/doctype/support_agent_investigation" "press/incident_management/support_agent"
ruff format --check "press/incident_management/doctype/support_agent_investigation" "press/incident_management/support_agent"
python -m compileall "press/incident_management/doctype/support_agent_investigation" "press/incident_management/support_agent"
bench --site frappecloud.localhost migrate
```

Run Frappe tests with an explicit site:

```bash
bench --site <site> run-tests --app press --module press.incident_management.support_agent.test_redaction
bench --site <site> run-tests --app press --module press.incident_management.support_agent.test_report
bench --site <site> run-tests --app press --module press.incident_management.support_agent.test_investigation
```

`test_investigation` contains end-to-end tests that mock `prometheus_get` and `elasticsearch_post` at the HTTP client level and run the full `collect_site_context → generate_report` pipeline. No real database records or network calls are needed.
