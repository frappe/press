# Support Agent Investigation Spec

## Goal

Build a site-scoped support investigation workflow in Press that helps support agents inspect Frappe Cloud issues using only read-only, allowlisted platform facts.

The only required input is a site name or site domain.

## Non-Goals

- Do not query the hosted site's database.
- Do not read customer documents, users, emails, invoices, tickets, or billing records.
- Do not expose raw logs, raw request payloads, secrets, tokens, cookies, or stack traces to the report generator.
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
- `recommended_next_steps`: Safe follow-up steps.
- `confidence`: `Low`, `Medium`, `High`.
- `evidence_json`: Redacted evidence strings.
- `timeline_json`: Redacted timeline items.
- `errors_json`: Aggregated redacted error summary.
- `payload_json`: Full redacted structured payload.
- `failure_reason`: Redacted failure reason if the runner fails.

## Public API

The feature exposes only narrow whitelisted methods from the DocType controller.

- `create_investigation(site: str, run_now: bool = True) -> str`
- `get_investigation(name: str) -> dict`
- `SupportAgentInvestigation.start()`

All methods validate site access before returning data or starting work.

## Access Model

A site can be investigated if:

- the caller is a system user, or
- the caller has `System Manager`, or
- the caller has accepted support access for the target `Site`.

Site domains are resolved to their owning site before access validation.

## Collectors

Collectors return structured facts only. They intentionally avoid raw logs, raw agent output, request data, traceback, site database access, and customer-owned records.

Current collectors:

- Site health: lifecycle status, bench/server/cluster links, setup and monitoring flags, usage percentages.
- Bench health: bench status, worker configuration, deploy candidate/build, queue-related flags.
- App versions: bench app, source, release, hash.
- Deployment timeline: recent `Site Update` records and safe status/timing fields.
- Background jobs: recent `Agent Job` metadata and counts by status, excluding output/request/traceback fields.
- Backups: recent backup status and safe size/status metadata, excluding URLs.
- Domains: counts/status metadata only, excluding domain names and DNS response bodies.
- Platform incidents: active incident metadata matching the site's server or cluster.
- Error summary: aggregated failed job counts by job type, excluding raw output and stack traces.

## Redaction

All collected payloads pass through `redact` before report generation and persistence.

The redactor removes:

- email addresses,
- phone numbers,
- IPv4 addresses,
- bearer tokens,
- authorization headers,
- common secret assignments,
- values under secret-like keys such as `password`, `secret`, `token`, `api_key`, `apikey`, and `cookie`.

Redaction version: `support-agent-redaction-v1`.

## Report Generation

The current implementation is deterministic and rule-based. It does not call an LLM yet.

It flags signals such as:

- inactive/broken/suspended site status,
- non-active bench status,
- failed or running site updates,
- recent failed agent jobs,
- critical disk/database/CPU usage,
- broken site domains,
- latest failed backup,
- matching active platform incidents.

The report generator returns:

- `summary`,
- `likely_cause`,
- `recommended_next_steps`,
- `confidence`,
- `evidence`,
- `timeline`.

## LLM Extension Point

If an LLM is added later, Press should continue to gather and redact all facts first. The model should receive only the redacted structured payload and should not receive tool access to generic Press APIs.

Safe future flow:

```text
Support Agent Investigation
  -> allowlisted collectors
  -> redaction
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
