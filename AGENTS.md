# Press App - Agent Notes

## Coding style

@taste.md

## Commit messages

@commit-guidelines.md

## Running Tests

Before running tests, always ask the user which site to use.

Use the following command format (note: `--site` goes before `run-tests`, not after):

```bash
bench --site <site> run-tests --app press --module press.press.doctype.site_update.test_site_update
```

To run a single test:

```bash
bench --site <site> run-tests --app press --module press.press.doctype.site_update.test_site_update --test test_specific_thing
```

If the test site is missing doctypes, migrate it first (use `--skip-failing` to avoid getting blocked by unrelated errors):

```bash
bench --site <site> migrate --skip-failing
```

See [guide-to-testing.md](guide-to-testing.md) for how to write tests for this project, and the [Frappe testing docs](https://docs.frappe.io/framework/user/en/testing) for framework-level testing reference.

## Running UI Tests (Playwright)

See [guide-to-ui-testing.md](guide-to-ui-testing.md) for setup and conventions.

Quick reference — run from `dashboard/`:

```bash
# Headed (opens browser)
yarn test:e2e:headed

# Single file
npx playwright test tests-e2e/tests/dashboard/site-update-banner.test.ts --headed
```

Requires a running bench (`bench start`) and `dashboard/tests-e2e/.env` with credentials.

## Linting and Formatting

Python (via ruff — runs on pre-commit):
```bash
ruff check press/
ruff format press/
```

JavaScript/Vue (via Biome):
```bash
npx biome check dashboard/
npx biome format dashboard/
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

## Finding docs.frappe.io/cloud URLs

Error messages and dialogs often link to Frappe Cloud docs. Don't guess slugs —
they 404 (the uninstall page is `how-to-uninstall-an-app-from-the-site`, not
`sites/uninstall-an-app`). Search the wiki API instead:

```bash
curl -s "https://docs.frappe.io/api/method/wiki.frappe_wiki.doctype.wiki_document.search.search?query=<TERM>&space=0uh9cfn2fk"
```

Returns `{message:{results:[{title, route, content, score}], total}}`. Take the
top result's `route` and prepend `https://docs.frappe.io/`. `space=0uh9cfn2fk`
scopes results to the **Cloud** space (all routes start with `cloud/`); omit
`space` to search all of docs.frappe.io (framework, etc.).

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
