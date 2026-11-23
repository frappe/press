# Self-hosted runner for the workflows in .github/workflows/.
# The base image is Ubuntu 24.04 with a "runner" user, passwordless sudo and
# the Docker binaries, like GitHub's ubuntu-24.04 image.
FROM ghcr.io/actions/actions-runner:2.338.2

# The default Node of GitHub's ubuntu-24.04 image is 22. Workflows that call
# setup-node without a version use it. commitlint needs 22.12 or later.
ARG NODE_VERSION=22.23.5

USER root

# GitHub's runners use UTC. Without a time zone, Chromium reports
# "Etc/Unknown" and dayjs throws when the dashboard formats a date.
ENV TZ=Etc/UTC

# Docker's helper that lets dockerd run inside a container on cgroup v2.
COPY --from=docker:29-dind /usr/local/bin/dind /usr/local/bin/dind

# Tools that GitHub's ubuntu-24.04 image has and the workflows use, and the
# packages of the "Cache apt" steps in main.yaml, which self-hosted jobs skip.
# ponytail: list found by reading the workflows; add packages here when a job
# fails with "command not found" or a missing library.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        iptables build-essential pkg-config xz-utils cron tzdata \
        python-is-python3 gh \
        mariadb-client libmariadb-dev \
        redis-server libcups2-dev \
    && curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
        | tar -xJ -C /usr/local --strip-components=1 \
    && npm install -g yarn \
    && npx -y playwright@1.54 install-deps chromium \
    && groupadd -f systemd-journal \
    && rm -rf /var/lib/apt/lists/*

# All runners on the VM share the pip and yarn caches in /cache, like the
# BuildKit cache mounts in press/docker/Dockerfile. pip is safe to share.
# Two yarn v1 installs that write one cache at the same time can corrupt it,
# so the Install step of Setup Bench holds a lock (main.yaml). Do not use
# yarn's own --mutex: the press postinstall runs yarn inside yarn, and the
# inner yarn then waits forever for the lock that its parent holds.
ENV PIP_CACHE_DIR=/cache/pip
RUN printf 'cache-folder "/cache/yarn"\n' > /home/runner/.yarnrc \
    && chown runner:runner /home/runner/.yarnrc

COPY runner.sh cleanup.sh /usr/local/bin/

ENTRYPOINT ["/usr/local/bin/runner.sh"]
