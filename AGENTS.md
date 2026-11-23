# Press App - Agent Notes

## Guidelines

Each guideline file applies to one kind of task. Read the file for your task
before you start. Do not read the other files.

- Before you write or review code, read [coding-guidelines.md](coding-guidelines.md).
- Before you write a commit message, read [commit-guidelines.md](commit-guidelines.md).
- Before you open a pull request, read [pr-guidelines.md](pr-guidelines.md).
- Before you run or write tests, read [testing-guidelines.md](testing-guidelines.md).
- Before you lint or format code, read [linting-guidelines.md](linting-guidelines.md).
- Before you build the frontend, read [build-guidelines.md](build-guidelines.md).

## Finding docs.frappe.io/cloud URLs

Error messages and dialogs often link to Frappe Cloud docs. Do not guess a slug.
A guess gives a 404. The uninstall page is `how-to-uninstall-an-app-from-the-site`,
not `sites/uninstall-an-app`. Search the wiki API instead:

```bash
curl -s "https://docs.frappe.io/api/method/wiki.frappe_wiki.doctype.wiki_document.search.search?query=<TERM>&space=0uh9cfn2fk"
```

The call returns `{message:{results:[{title, route, content, score}], total}}`.
Take the `route` of the top result and put `https://docs.frappe.io/` before it.
`space=0uh9cfn2fk` limits the results to the **Cloud** space, where all routes
start with `cloud/`. Omit `space` to search all of docs.frappe.io, which
includes the framework documentation.

## Architecture

Press is a [Frappe](https://github.com/frappe/frappe) app that powers Frappe Cloud — a self-serve cloud hosting platform for the Frappe stack.

- Frappe framework docs: https://docs.frappe.io/framework/
- Frappe Cloud user docs: https://docs.frappe.io/cloud

### Two main layers

**Backend** (`press/`): A Frappe app. The business logic lives in the doctypes at `press/press/doctype/`. The REST API for the dashboard is in `press/api/`. `press/hooks.py` registers the scheduled tasks and the document events.

**Frontend** (`dashboard/`): A Vue 3 single-page application, built with [Frappe UI](https://github.com/frappe/frappe-ui). Pages live in `dashboard/src/pages/`, and reusable components in `dashboard/src/components/`. The frontend calls the whitelisted Python methods in `press/api/`.

### Core entity hierarchy

There are two parallel dependency chains that meet at **Bench**:

**App/release chain** (what runs on a bench):
```
App
 └── AppSource (a branch of a GitHub repo)
      └── AppRelease (a specific commit)
           └── ReleaseGroup (a set of AppSources + their versions, user-facing "Bench group")
                └── DeployCandidate (snapshot of a group ready to be built)
                     └── DeployCandidateBuild (the Docker build, one for arm64 and one for x86_64)
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

`press/agent.py` holds the `Agent` class. It is the only interface from Press to the [Agent](https://github.com/frappe/agent) flask app on each server. Every operation on a remote server goes through `Agent`, which creates an `AgentJob` record and sends an HTTP request. Site creation, app installation, and backups all work this way. `poll_pending_jobs` runs every 5 seconds. It polls the open jobs and dispatches the callback of each job that is complete.

### Infrastructure automation

The Ansible playbooks in `press/playbooks/` provision the servers. `DeployCandidateBuild` builds the Docker images for the benches. The `VirtualMachine` doctype manages the machines through the API of each cloud provider: AWS, Hetzner, OCI, and Frappe Compute.
