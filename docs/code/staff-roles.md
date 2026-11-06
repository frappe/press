# Staff roles

Frappe Cloud employees get access through scope roles, not through System
Manager. Each scope role gives full access to one area. A Role Profile combines
the scope roles that one job needs. Give an employee a Role Profile. Give System
Manager only to the few admins who need shells and secrets.

## Scope roles

| Role | Scope |
|------|-------|
| Press Support Manager | Teams, sites, site backups, site updates, domains, support access, webhooks |
| Press Infrastructure Manager | Servers, virtual machines, clusters, agent jobs, Press jobs, monitoring, incidents, cloud cost |
| Press Release Manager | Apps, app sources, app releases, release groups, benches, deploy candidates, builds, deploys |
| Press Billing Manager | Invoices, payments, payouts, subscriptions, usage records, plans |
| Press Security Manager | Wazuh, malware scans, abuse reports, blocked domains, audit logs and User 2FA (read only) |
| Press SSH Manager | SSH keys, SSH certificates, SSH access audits |
| Press Product Manager | SaaS apps, product trials, dashboard banners, notifications, feedback |
| Press Marketplace Manager | Marketplace apps, app reviews, release approvals |
| Partner Manager | Partners, partner leads, certificates, consultants |

The scopes do not share read access. For example, a Billing Manager cannot open
a Site. Add a second scope role or a second Role Profile when a job needs both.

## Role Profiles

| Role Profile | Roles |
|--------------|-------|
| Press Support Engineer | Support, Release |
| Press Site Reliability Engineer | Infrastructure, Release, Support |
| Press Security Engineer | Security, Infrastructure |
| Press SSH Access Manager | SSH Manager |
| Press Finance | Billing |
| Press Product Team | Product |
| Press Marketplace Team | Marketplace |
| Press Partnerships | Partner Manager |

A user can have more than one Role Profile.

## System Manager only

These DocTypes give shell access to servers or hold secrets. They grant no
scope role:

- Ansible Console, Bench Shell, Build Cache Shell, and their logs
- Serial Console Log
- Certificate Authority, SSH Certificate Authority

An SSH certificate gives shell access to servers, so Press SSH Manager is a
role of its own, in its own Role Profile. No other profile includes it. The
SSH Certificate Authority, which holds the signing key, stays System Manager
only.
- Press Settings, Payment Gateway, Mpesa Setup, Mail Setup, Telegram Group
- Saas Remote Login, Site Access Token

Press Infrastructure Manager only reads these DocTypes:

- Agent Job: creating or editing a job sends any request to a server agent,
  which reaches the build cache shell and customer databases.
- Press Job Type: its step scripts run through `safe_exec`.
- Press Workflow, Press Workflow Task, Press Workflow Object and Press Workflow
  Test: a task calls the method and arguments that it names, and objects are
  loaded with `pickle`. The workflow engine inserts these records itself, so
  Press Jobs still work.

Press Release Manager only reads App Rename, because site updates run its
before-migrate and rollback scripts on customer benches.

The `action_script` field of Dashboard Banner is at permlevel 1, which only
System Manager can read or write. The script runs as JavaScript in every
customer's dashboard. Press Product Manager can still create banners.

These actions also stay System Manager only: `Team.impersonate`,
`Site.forcefully_remove_site`, `Managed Database Service.show_root_password`,
the MCP endpoint, and Grove credential rotation. `frappe.client.get_password`
is System Manager only in Frappe, so Password fields stay hidden from scope
roles.

## Where the rules live

- The permission rows are in each DocType JSON. The `roles` table is in each
  report JSON. A report needs `report` permission on its `ref_doctype`, so a
  report gets the role that owns that DocType.
- Code-level checks use `frappe.only_for([...])` with System Manager and the
  scope role.
- The roles ship in `press/fixtures/role.json`. The profiles ship in
  `press/fixtures/role_profile.json`.
- `press/tests/test_staff_role_scopes.py` fails when a new DocType grants
  System Manager but no scope role. Add a scope role to the new DocType, or add
  it to `SYSTEM_MANAGER_ONLY` in that test.
