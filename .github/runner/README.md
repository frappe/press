# Self-hosted runners for press CI

These files set up GitHub Actions runners for `frappe/press` on a VM that you own.

## How it works

Each runner is a Docker container. The container also runs its own Docker daemon. Jobs on one VM therefore do not share port 3306, the `mariadb` container name, or `/home/runner/frappe-bench`.

The image is `ghcr.io/actions/actions-runner` (Ubuntu 24.04), plus the tools that the jobs need and that GitHub's `ubuntu-24.04` image has. The `Dockerfile` lists these tools.

GitHub-hosted runners give each job a new VM. Here, a container runs many jobs. Before each job, `cleanup.sh` removes the containers, `~/frappe-bench` and `/data` that the previous job left.

The repository variable `SELF_HOSTED_RUNNERS` selects the runners for every workflow in `.github/workflows/`:

- When the value is `true`, the jobs use the self-hosted runners. Pull requests from forks still use GitHub-hosted runners, so code from a fork never runs on your VM.
- When the value is different, or the variable does not exist, all jobs use GitHub-hosted runners.

GitHub does not move a job to a GitHub-hosted runner when no self-hosted runner is online. The job waits for up to 24 hours. If the VM stops, set `SELF_HOSTED_RUNNERS` to `false` in Settings → Secrets and variables → Actions → Variables, then run the waiting workflows again.

| File | Purpose |
| --- | --- |
| `Dockerfile` | The runner image |
| `runner.sh` | The entrypoint: starts dockerd, registers the runner on the first start, then runs it |
| `cleanup.sh` | The job-started hook |
| `compose.yaml` | Starts N runners on one VM |

## Requirements

- An x86_64 VM with Ubuntu. The first VM has Ubuntu 26.04. The VM needs outbound internet access only.
- Memory and CPU for each runner. One CI run uses 4 runners at the same time. A VM with 16 host threads and 60 GB of memory runs 6 runners.
- Admin access to `frappe/press`, to get a registration token.

> **CAUTION:** Use a VM that runs nothing else. The containers are privileged, so a job has root access to the VM.

Before you use the runners, go to Settings → Actions → General on `frappe/press`. Make sure that workflows from fork pull requests need approval.

## Install

Do these steps as root on the VM, unless the step says "on your computer".

1. Install Docker:

   ```sh
   apt-get update
   apt-get install -y docker.io docker-compose-v2 docker-buildx
   ```

2. On your computer, copy this directory to `/opt/runner` on the VM:

   ```sh
   scp -r .github/runner root@<vm>:/opt/runner
   ```

3. Get a registration token. Go to Settings → Actions → Runners → New self-hosted runner, and copy the value after `--token`. Or, on your computer, use the GitHub CLI:

   ```sh
   gh api -X POST repos/frappe/press/actions/runners/registration-token -q .token
   ```

4. Write the `.env` file. Use a different `RUNNER_PREFIX` on each VM, for example `vm101` and `vm102`:

   ```sh
   cd /opt/runner
   (umask 077; printf 'RUNNER_PREFIX=vm101\nRUNNER_TOKEN=<token>\n' > .env)
   ```

5. Build the image and start the runners:

   ```sh
   docker compose up -d --build --scale runner=6
   ```

6. After one minute, make sure that the runners are online. Each runner name is `<RUNNER_PREFIX>-<container id>`:

   ```sh
   docker compose ps
   docker compose logs runner | grep 'Listening for Jobs'
   ```

   On GitHub, the runners show in Settings → Actions → Runners.

The token expires after one hour. A runner uses the token only when it registers. The containers restart after a reboot and do not register again.

## Update the image

Do this when you change the `Dockerfile` or the scripts. New containers register again, so you need a new token.

1. Make sure that no runner is busy. On your computer:

   ```sh
   gh api repos/frappe/press/actions/runners -q '.runners[] | "\(.name) busy=\(.busy)"'
   ```

2. Copy the changed files to `/opt/runner` on the VM.
3. Get a new token, and put it in `.env` (Install, steps 3 and 4).
4. Replace the runners:

   ```sh
   cd /opt/runner
   docker compose build
   docker compose down
   docker compose up -d --scale runner=6
   ```

5. Remove the old runners of this VM from GitHub. If you do not remove them, GitHub shows them as offline for 14 days. On your computer, set `P` to the `RUNNER_PREFIX` of the VM:

   ```sh
   P=vm101
   gh api repos/frappe/press/actions/runners \
     -q ".runners[] | select(.status==\"offline\" and (.name|startswith(\"$P-\"))) | .id" |
     while read -r id; do gh api -X DELETE "repos/frappe/press/actions/runners/$id"; done
   ```

## Change the number of runners

To add runners, put a new token in `.env`. Then start more containers, and keep the current ones:

```sh
docker compose up -d --no-recreate --scale runner=8
```

To remove runners, set a lower number. Then remove the offline runners from GitHub (Update the image, step 5).

## Remove the runners

```sh
cd /opt/runner
docker compose down
```

Then remove the offline runners from GitHub (Update the image, step 5).

## Troubleshooting

- **A job fails with "command not found" or a missing library.** GitHub's image has the tool, and this image does not. Add the package to the `apt-get install` line in the `Dockerfile`. Then update the image. `cron`, `tzdata` and `python-is-python3` were added for this reason.
- **The runners are offline.** Look at `docker compose ps` and `docker compose logs runner`.
- **Docker fails inside a job.** The log of the inner Docker daemon is in the container:

  ```sh
  docker compose exec --index 1 runner cat /var/log/dockerd.log
  ```

- **Registration fails.** The token expired. Get a new token, put it in `.env`, and start the runners again.
