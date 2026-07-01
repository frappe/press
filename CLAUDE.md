# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tests and coding style

@AGENTS.md
@taste.md

## Commit messages

@commit-guidelines.md

## Linting and Formatting

Python (via ruff — runs on pre-commit):
```bash
ruff check press/
ruff format press/
```

JavaScript/Vue (via Biome). Do NOT use `npx biome` — it resolves to an unrelated
package (v0.3.3) that silently does nothing. Use the real Biome (v2.x) installed by
the pre-commit hook, with the repo-root `biome.json` and absolute file paths:
```bash
BIOME=$(ls ~/.cache/pre-commit/*/node_env-default/lib/node_modules/@biomejs/pre-commit/node_modules/@biomejs/cli-linux-x64/biome | head -1)
"$BIOME" check --write --config-path="$(pwd)/biome.json" <absolute-paths>
```

Set up pre-commit hooks once with:
```bash
bash setup-pre-commit.sh
```

## Building the Frontend

```bash
cd dashboard && yarn dev       # development server
cd dashboard && yarn build     # production build
yarn build                     # builds dashboard + email/marketplace/saas CSS
```

## Architecture

Press is a [Frappe](https://github.com/frappe/frappe) app that powers Frappe Cloud — a self-serve cloud hosting platform for the Frappe stack.

- Frappe framework docs: https://docs.frappe.io/framework/
- Frappe Cloud user docs: https://docs.frappe.io/cloud

### Two main layers

**Backend** (`press/`): A Frappe app. Business logic lives in doctypes at `press/press/doctype/`. The REST API consumed by the dashboard is in `press/api/`. Scheduled tasks and event hooks are wired up in `press/hooks.py`.

**Frontend** (`dashboard/`): A Vue 3 SPA using [Frappe UI](https://github.com/frappe/frappe-ui). Pages live in `dashboard/src/pages/`, reusable components in `dashboard/src/components/`. The frontend calls the whitelisted Python API methods in `press/api/`.

### Core entity hierarchy

There are two parallel dependency chains that meet at **Bench**:

**App/release chain** (what runs on a bench):
```
App
 └── AppSource (a branch of a GitHub repo)
      └── AppRelease (a specific commit)
           └── ReleaseGroup (a set of AppSources + their versions, user-facing "Bench group")
                └── DeployCandidate (snapshot of a group ready to be built)
                     └── DeployCandidateBuild (the Docker build; separate arm64 / x86_64)
```

**Infrastructure chain** (where a bench runs):
```
Cluster (a cloud region)
 └── VirtualMachine (a cloud VM)
      ├── Server (app server — runs gunicorn/redis)
      ├── DatabaseServer (runs MariaDB)
      └── ProxyServer (runs nginx)
```

**Bench** is where the two chains converge — it references a ReleaseGroup, a DeployCandidate, a DeployCandidateBuild, and a Server (paired with a DatabaseServer). **Site** lives on a Bench and belongs to a Team.

The creation flow: `group.create_deploy_candidate()` → `candidate.build()` → `Deploy` (calls `create_benches()`, creating `Bench` records on target servers) → sites are created on those benches.

Each key doctype has a `README.md` in its folder with more detail:
- [`agent_job/`](press/press/doctype/agent_job/README.md) — how Press talks to servers
- [`server/`](press/press/doctype/server/README.md) — Server, DatabaseServer, ProxyServer
- [`release_group/`](press/press/doctype/release_group/README.md) — user-facing bench group
- [`deploy_candidate/`](press/press/doctype/deploy_candidate/README.md) — build snapshot
- [`deploy_candidate_build/`](press/press/doctype/deploy_candidate_build/README.md) — Docker image build
- [`bench/`](press/press/doctype/bench/README.md) — running bench on a server
- [`site/`](press/press/doctype/site/README.md) — the Frappe site
- [`site_update/`](press/press/doctype/site_update/README.md) — moving a site to a newer bench

### Agent communication

`press/agent.py` contains the `Agent` class — the sole interface for Press to talk to the [Agent](https://github.com/frappe/agent) flask app running on each server. Every operation on a remote server (create site, install app, run backup, etc.) goes through `Agent`, which creates an `AgentJob` record and sends an HTTP request. Agent jobs are polled via `poll_pending_jobs` (runs every 5 seconds) and callbacks are dispatched on completion.

### Infrastructure automation

Ansible playbooks in `press/playbooks/` handle server provisioning. Docker images for benches are built by `DeployCandidateBuild`. Virtual machines are managed via cloud provider APIs (AWS, Hetzner, OCI, Frappe Compute) through the `VirtualMachine` doctype.
