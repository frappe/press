# Self-hosted runners for press CI

These files set up GitHub Actions runners for `frappe/press` on a VM that you own.

## How it works

Each runner is a Docker container. The container also runs its own Docker daemon. Jobs on one VM therefore do not share port 3306, the `mariadb` container name, or `/home/runner/frappe-bench`.

The image is `ghcr.io/actions/actions-runner` (Ubuntu 24.04), plus the tools that the jobs need and that GitHub's `ubuntu-24.04` image has. The `Dockerfile` lists these tools.

GitHub-hosted runners give each job a new VM. Here, a container runs many jobs. Before each job, `cleanup.sh` stops the processes and removes the containers, `~/frappe-bench` and `/data` that the previous job left.

Self-hosted jobs do not use GitHub's cache. All runners on the VM share the pip and yarn caches in `/opt/runner-cache/pip` and `/opt/runner-cache/yarn`. The Install step of Setup Bench holds a file lock (`flock /cache/yarn/.lock`), so two installs do not write the yarn cache at the same time. Do not use yarn's own `--mutex`: the press postinstall runs yarn inside yarn, and the inner yarn waits forever for its parent's lock. Setup Bench copies the bench and the MariaDB data to `/opt/runner-cache/runs/<run id>` on the VM. The Client and Server jobs copy the MariaDB data from there. They mount the bench with overlayfs (`.github/helper/mount-bench.sh`), so the saved bench stays read-only and each job writes its changes to an `overlay.*` directory next to it. `cleanup.sh` removes runs older than one day. Each run uses some GB of disk. This works only while all runners are on one VM.

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
| `prune.sh` | Weekly cron job: stops the runners, removes unused Docker data and saved runs, then starts the runners. Clears the pip and yarn caches on the first Sunday of each month |
| `rolling.sh` | Runs on your computer: replaces the runners with containers of a new image, one idle runner at a time |

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

7. Install the weekly prune. Each image rebuild leaves an old image, build cache and the volumes of the replaced containers, and the shared caches grow. The prune waits up to 30 minutes for running jobs, then stops the runners for about one minute. Cron runs it on Sunday morning. On the first Sunday of each month, it also clears the pip and yarn caches:

   ```sh
   install -m 755 /opt/runner/prune.sh /etc/cron.weekly/runner-prune
   ```

The token expires after one hour. A runner uses the token only when it registers. The containers restart after a reboot and do not register again.

## Update the image

Do this when you change the `Dockerfile` or the scripts. Running jobs continue during the update.

1. Copy the changed files to `/opt/runner` on the VM.
2. Build the new image on the VM:

   ```sh
   cd /opt/runner
   docker compose build
   ```

3. On your computer, replace the runners. Give the SSH destination of the VM and its `RUNNER_PREFIX`. The script keeps the number of runners that run on the VM now. To change the number, give it as the third argument:

   ```sh
   .github/runner/rolling.sh root@<vm> vm101
   ```

   If you reach the VM through a jump host, put the jump host in `~/.ssh/config`, because the script gives `ssh` only the destination:

   ```
   Host runner-vm101
       HostName <vm>
       User root
       ProxyJump root@<jump host>
   ```

   Then use `runner-vm101` as the SSH destination.

   For each container that uses an old image, the script waits until the runner is idle. Then it deletes the runner on GitHub, writes a new token to `.env`, and starts a new container in its place. When a job is long, the script waits for it.

## Remove offline runners from GitHub

GitHub shows a removed runner as offline for 14 days. To remove the offline runners of a VM, set `P` to the `RUNNER_PREFIX` of the VM. On your computer:

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

To remove runners, set a lower number. Then remove the offline runners from GitHub (see Remove offline runners from GitHub).

## Remove the runners

```sh
cd /opt/runner
docker compose down -v
```

Then remove the offline runners from GitHub (see Remove offline runners from GitHub).

## Troubleshooting

- **A job fails with "command not found" or a missing library.** GitHub's image has the tool, and this image does not. Add the package to the `apt-get install` line in the `Dockerfile`. Then update the image. `cron`, `tzdata` and `python-is-python3` were added for this reason.
- **The runners are offline.** Look at `docker compose ps` and `docker compose logs runner`.
- **Docker fails inside a job.** The log of the inner Docker daemon is in the container:

  ```sh
  docker compose exec --index 1 runner cat /var/log/dockerd.log
  ```

- **Registration fails.** The token expired. Get a new token, put it in `.env`, and start the runners again.
- **rolling.sh stops with an SSH error.** The connection to the VM dropped. Run the script again. It continues with the runners that still use the old image.
- **rolling.sh does not replace a runner.** GitHub does not delete a runner while it runs a job. The API returns HTTP 422 ("is currently running a job and cannot be deleted"). The script tries again on each pass and replaces the runner when it is idle. Do not remove the container by hand, because that stops the job.
- **Every job on a runner fails in "Set up runner" with `Device or resource busy`.** An earlier job left a mount at `~/frappe-bench`, and `cleanup.sh` cannot remove a mount point. The Client and Server jobs mount the bench with `.github/helper/mount-bench.sh`. They unmount it in their last step, and `cleanup.sh` unmounts it before the next job. A runner on an image older than that `cleanup.sh` keeps the mount. To find the runners with a mount:

  ```sh
  cd /opt/runner && for c in $(docker compose ps -q); do echo "$(docker inspect -f '{{.Name}}' $c) $(docker exec $c grep -c ' /home/runner/frappe-bench overlay' /proc/mounts)"; done
  ```

  To remove the mounts, run this on the VM. Running jobs continue:

  ```sh
  cd /opt/runner && for c in $(docker compose ps -q); do docker exec "$c" sh -c 'umount --lazy /home/runner/frappe-bench 2>/dev/null; true'; done
  ```

  Then update the image, so that `cleanup.sh` unmounts the bench.
