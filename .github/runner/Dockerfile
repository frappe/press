# Self-hosted runner for the bench jobs in .github/workflows/main.yaml.
# The base image is Ubuntu 24.04 with a "runner" user, passwordless sudo and
# the Docker binaries, like GitHub's ubuntu-24.04 image.
FROM ghcr.io/actions/actions-runner:2.338.2

USER root

# GitHub's runners use UTC. Without a time zone, Chromium reports
# "Etc/Unknown" and dayjs throws when the dashboard formats a date.
ENV TZ=Etc/UTC

# Docker's helper that lets dockerd run inside a container on cgroup v2.
COPY --from=docker:29-dind /usr/local/bin/dind /usr/local/bin/dind

# Tools that GitHub's ubuntu-24.04 image has and main.yaml / install.sh use.
# ponytail: list found by reading main.yaml; add packages here when a job
# fails with "command not found" or a missing library.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        iptables build-essential pkg-config wget xz-utils cron tzdata \
        python-is-python3 gh \
        mariadb-client libmariadb-dev \
        fontconfig libxrender1 libxext6 libjpeg-turbo8 \
        nodejs npm \
    && npm install -g yarn \
    && npx -y playwright@1.54 install-deps chromium \
    && groupadd -f systemd-journal \
    && rm -rf /var/lib/apt/lists/*

COPY runner.sh cleanup.sh /usr/local/bin/

ENTRYPOINT ["/usr/local/bin/runner.sh"]
