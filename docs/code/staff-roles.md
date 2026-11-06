# Staff roles

Frappe Cloud employees get access through scope roles, not through System
Manager. Each scope role gives full access to one area. A Role Profile combines
the scope roles that one job needs. Give an employee a Role Profile. Give System
Manager only to the few admins who need shells and secrets.

## Scope roles

| Role | Scope |
|------|-------|
| Press Support | First-line support (L1) that finds issues. Reads everything that Press Support Engineer reads and changes nothing. Presses only buttons marked `@safe_for_readers`. Can also run the MariaDB and customer email reports, request team deletion, transfer resources between teams and rotate site passwords |
| Press Support Engineer | Engineering support (L2). Full access to teams, sites, backups, updates, domains, webhooks, apps, release groups, benches and deploys. Read, write and every button on servers, database servers, proxy servers and virtual machines, but not create or delete. Create on TLS certificates, server activities and Press notifications, which buttons make as a side effect. Read only on agent jobs, Press jobs, incidents, restorations, TLS certificates, billing, Marketplace, Product and Partner records |
| Press Infrastructure Manager | Servers, virtual machines, clusters, agent jobs, Press jobs, monitoring, incidents, cloud cost |
| Press Release Manager | Apps, app sources, app releases, release groups, benches, deploy candidates, builds, deploys |
| Press Billing Manager | Invoices, payments, payouts, subscriptions, usage records, plans |
| Press Security Manager | Wazuh, malware scans, abuse reports, blocked domains, audit logs and User 2FA (read only) |
| Press SSH Manager | SSH keys, SSH certificates, SSH access audits |
| Press Product Manager | SaaS apps, product trials, dashboard banners, notifications, feedback |
| Press Marketplace Manager | Marketplace apps, app reviews, release approvals |
| Partner Manager | Partners, partner leads, certificates, consultants |

Except for the two support roles, the scopes do not share read access. For example, a
Billing Manager cannot open a Site. Add a second scope role or a second Role
Profile when a job needs both.

Read only on a DocType does not stop the buttons on it, because Frappe runs a
whitelisted document method for any user who can read the record. So
`@needs_staff_role(...)` in `press/access/staff_roles.py` marks the buttons that
belong to one scope: on Invoice, Subscription, Marketplace App, Marketplace App
Subscription, Product Trial Request and Partner Approval Request, the TLS
Certificate private key, and the on-prem failover config on Server. The
`check_staff_role` `before_request` hook stops desk staff without that role when
they call the method from desk. Press code that calls the method, and customers
on the dashboard, are not affected. Press Support Engineer can press the
buttons on agent jobs, Press jobs, restorations and incidents.

Press Support is listed in `READ_ONLY_ROLES`. When a staff user reads a DocType
only through a read-only role, `check_staff_role` lets them call only the
methods marked `@safe_for_readers`, such as `Site.get_backup_schedule` or
`Server.ping_agent`. Mark a method safe only when it changes no record, queues
no job and returns no secret. The rule also covers `press.api.client.run_doc_method`
and `press.api.client.delete`. Other dashboard APIs still let every System User
through, so Press Support is read only in desk but not yet on the dashboard.

Desk sends the whole form with a button call, and Frappe checks only read
access. So `use_saved_document`, also a `before_request` hook, runs the button
on the saved record when the staff user cannot write it, and refuses a new
record that they cannot create. This is why the engine code for Agent Job,
Agent Job Step, Ansible Play, Ansible Task, Press Job, Press Job Step and the
`StepHandler` in `press/runner.py` can insert and save with
`ignore_permissions`: read-only staff press their buttons without create or
write rights, and still cannot change what the engine sends.

Plan changes stay with Billing: Support cannot create a Site Plan Change or a
Plan Change, because both write a Subscription.

These fields hold secrets in plain text and are at permlevel 1. Of the staff
roles, only System Manager and the owning scope role read them:
Agent Job `request_data` and `request_files`, Ansible Play `variables`, and the
`secret_key` of Marketplace App Subscription and Saas App Subscription.

## Role Profiles

| Role Profile | Roles |
|--------------|-------|
| Press Support | Press Support (L1) |
| Press Support Engineer | Press Support Engineer (L2) |
| Press Site Reliability Engineer | Infrastructure, Press Support Engineer |
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

Press Release Manager and the support roles only read App Rename, because site updates run its
before-migrate and rollback scripts on customer benches.

The `action_script` field of Dashboard Banner is at permlevel 1, which only
System Manager can read or write. The script runs as JavaScript in every
customer's dashboard. Press Product Manager can still create banners.

The Product Trial fields `suspension_email_content`, `email_header_content` and
`email_account` are at permlevel 1 for the same reason. The server renders the
suspension email as Jinja, which can read any table. The header is raw HTML in
the sign-up email. The email account picks the sender of trial emails.

These methods return secrets and stay System Manager only: `show_agent_password`
on servers, `show_admin_password` on Site, the password methods on monitor,
analytics, registry, log and trace servers, and
`VirtualMachine.get_serial_console_credentials`.

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
