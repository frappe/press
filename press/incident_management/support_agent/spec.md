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
- **Web error log**: Recent ERROR and CRITICAL entries from `web.error.log` on the site's app server. Only the gunicorn-level description and the final exception message line are captured — not full stack frames with local variables. All entries are redacted before being stored. Collects at most 10 error blocks from the last 500 log lines.
- **Site performance summary**: Up to 20 slowest endpoints from Elasticsearch over the last 24 hours. Each endpoint includes average and peak duration, a `spike_detected` flag (peak ≥ 3× mean and peak > 2 s), and an `is_custom` flag indicating whether the endpoint belongs to a non-Frappe app. App origin is determined by checking `repository_owner` on the AppSource record — any owner other than `frappe` is treated as custom. Also includes a `has_custom_apps` flag indicating whether any non-Frappe apps are installed on the bench.

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
- matching active platform incidents.

Confidence is `High` if any blocking signal is present (non-Active site or bench, fatal deployment, failed jobs, or active incidents), `Medium` if other causes were found, and `Low` if no causes were found.

The report generator returns:

- `summary`,
- `likely_cause`,
- `recommended_next_steps`,
- `confidence`,
- `evidence`,
- `timeline`.

## LLM Extension Point

The LLM integration path is gated entirely on redaction. No payload may reach the model unless it has been processed by `redact` first. This is a hard requirement, not a best-effort measure — the model must never receive PII.

When LLM support is added:

- Collect all facts via the allowlisted collectors.
- Run the full redaction pass.
- Send only the redacted structured payload to the model.
- The model must not receive tool access to generic Press APIs.
- The `llm_model` field on the DocType records which model processed the investigation.
- The LLM response must be validated before being persisted to `summary`, `likely_cause`, `recommended_next_steps`, and `confidence`.

Safe future flow:

```text
Support Agent Investigation
  -> allowlisted collectors
  -> redaction          ← PII boundary; nothing crosses this line not yet redacted
  -> structured report prompt
  -> LLM response validation
  -> persisted report
```

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
```
