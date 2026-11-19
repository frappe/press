#!/bin/bash
# Entrypoint, runs as root. Starts this container's own dockerd, registers the
# runner the first time, then runs it as the "runner" user.
set -euo pipefail

rm -f /var/run/docker.pid
dind dockerd --group docker >/var/log/dockerd.log 2>&1 &
timeout 60 bash -c 'until docker info >/dev/null 2>&1; do sleep 1; done'

mkdir -p /cache/runs /cache/pip /cache/yarn
chown runner:runner /cache /cache/runs /cache/pip /cache/yarn

cd /home/runner
if [ ! -f .runner ]; then
	runuser -u runner -- ./config.sh --unattended --replace \
		--url "$RUNNER_URL" --token "$RUNNER_TOKEN" \
		--name "$RUNNER_PREFIX-$(hostname)"
	echo "ACTIONS_RUNNER_HOOK_JOB_STARTED=/usr/local/bin/cleanup.sh" >>.env
fi

exec runuser -u runner -- ./run.sh
