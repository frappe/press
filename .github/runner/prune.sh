#!/bin/sh
# Weekly cron job on the runner VM: /etc/cron.weekly/runner-prune (README.md).
# Removes Docker data that no runner container uses: the volumes of replaced
# containers, old runner images and the build cache.
docker volume prune -f
docker image prune -f
docker builder prune -af
