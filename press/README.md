# press

The Frappe app that runs Frappe Cloud. The dashboard in `../dashboard` talks to
the API in `api/`, and the API acts on the doctypes in `press/doctype/`.

Read [AGENTS.md](../AGENTS.md) for the architecture and the entity hierarchy.
Each core doctype has its own `README.md` next to its Python file.

## Where things are

| Path | What it holds |
| --- | --- |
| `press/` | The main Frappe module: all doctypes, reports, and the workspace |
| `api/` | Whitelisted methods that the dashboard calls |
| `agent.py` | The only interface to the Agent app on each server |
| `hooks.py` | Scheduled tasks, document events, and app configuration |
| `playbooks/` | Ansible playbooks and roles that provision servers |
| `docker/` | Dockerfiles and configuration for bench images, the registry, and the SSH proxy |
| `infrastructure/` | Doctypes for containers, pods, nodes, and machine migrations |
| `marketplace/` | Doctypes for the app marketplace. See its [README](marketplace/README.md) |
| `saas/` | Doctypes and API for the SaaS product flows. See its [README](saas/README.md) |
| `workflow_engine/` | Multi-step jobs with retries. See its [README](workflow_engine/README.md) |
| `partner/` | Doctypes for the partner program: leads, tiers, certificates, audits |
| `incident_management/` | Doctypes for incidents, patterns, and investigations |
| `access/` | Rules for support access, record ownership, and which tabs a user sees |
| `guards/` | Request guards for MFA, roles, teams, and sites. See the [docs](../docs/code/guards/index.md) |
| `mcp/` | MCP server tools and the redaction guardrail |
| `utils/` | Helpers shared across doctypes: billing, DNS, jobs, email, and more |
| `telemetry/` | Sentry and monitor helpers |
| `security/` | fail2ban helpers |
| `frappe_compute_client/` | Client for the Frappe Compute provider API |
| `www/` | Server-rendered web pages outside the dashboard |
| `templates/` | Jinja templates for emails and pages |
| `public/` | Static assets that the site serves |
| `patches/` | Migration patches. `patches.txt` sets the order |
| `fixtures/` | Records that install with the app, such as job types and roles |
| `scripts/` | Scripts for one-off audits, migrations, and CI checks |
| `tests/` | Tests that belong to no single doctype |
| `experimental/` | Doctypes that are not stable yet |

## Adding a doctype

Put it in `press/doctype/`. Use `infrastructure/`, `marketplace/`, `saas/`,
`partner/`, or `incident_management/` only when the doctype belongs to that
area. Each of these directories is a separate Frappe module.
