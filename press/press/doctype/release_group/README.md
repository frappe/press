# ReleaseGroup

The user-facing "Bench group". A ReleaseGroup defines a collection of apps (each pinned to an `AppSource` — a specific repo branch) along with their dependency versions (Python, Node, Bench, etc.) and the list of servers to deploy to.

All sites on a bench share the same ReleaseGroup. When a user adds an app or changes a version, they update their ReleaseGroup and then deploy.

## Key relationships

- Has many **AppSources** (each AppSource tracks a repo/branch for one app)
- Has many **Servers** (which servers this group's benches can live on)
- Produces **DeployCandidates** via `create_deploy_candidate()`
- Referenced by every **Bench** and **Site** in the group

## Deployment flow

```
ReleaseGroup.create_deploy_candidate()
  → DeployCandidate (snapshot of current apps + deps)
    → DeployCandidate.build()
      → DeployCandidateBuild (Docker image, arm64 + x86_64)
        → Deploy (triggers create_benches())
          → Bench per server
```

## Public vs private

Public groups share servers with other teams. Private groups have dedicated servers (requires a server plan). The `public` flag controls this.
