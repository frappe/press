# DeployCandidate

A snapshot of a `ReleaseGroup` at a point in time, capturing the exact app releases, dependency versions, and environment variables needed to build a Docker image. Created by `ReleaseGroup.create_deploy_candidate()`.

A DeployCandidate is immutable once built — it represents a specific, reproducible Docker image.

## Status lifecycle

```
Draft → Scheduled → Pending → Preparing → Running → Success
                                                    → Failure
```

## Builds

A DeployCandidate produces up to two Docker builds via `DeployCandidateBuild`:
- `intel_build` — x86_64 image (for most servers)
- `arm_build` — arm64 image (for ARM-based servers)

`candidate.build()` creates these. After both succeed, a `Deploy` can be created to roll out the candidate to servers.

## Key relationships

- Belongs to one **ReleaseGroup**
- Has two **DeployCandidateBuild** links (`intel_build`, `arm_build`)
- Referenced by every **Bench** created from this candidate
- Referenced by every **Deploy** that deploys this candidate
