#!/bin/bash
# Job-started hook. GitHub-hosted runners give each job a new VM; this removes
# what the previous job on this runner left, so main.yaml can assume the same.
docker rm -f $(docker ps -aq) >/dev/null 2>&1 || true
docker network prune -f >/dev/null
sudo rm -rf /home/runner/frappe-bench /data
