# DeployCandidateBuild

The actual Docker image build for a `DeployCandidate`. A candidate produces two builds — one for each CPU architecture:

- `intel_build` (x86_64) — used by most servers
- `arm_build` (arm64) — used by ARM-based servers

Both are referenced on the `DeployCandidate` record.

## Status lifecycle

```
Draft → Scheduled → Pending → Preparing → Running → Success
                                                   → Failure
```

## Build process

The build runs on a designated build server (`Server.use_for_build = 1`). Press uses Docker BuildKit to produce the image, which is then pushed to the registry. The build steps are streamed back and stored as `Deploy Candidate Build Step` child rows.

## Key relationships

- Belongs to one **DeployCandidate** and one **ReleaseGroup**
- References the **Server** used to run the build (`build_server`)
- Once successful, referenced by **Bench** records via `DeployCandidate.intel_build` / `arm_build`
