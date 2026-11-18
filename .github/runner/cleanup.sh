#!/bin/bash
# Job-started hook. GitHub-hosted runners give each job a new VM; this removes
# what the previous job on this runner left, so the workflows can assume the same.

# Processes from earlier jobs, for example the redis-server that "bench start"
# starts. One that survives keeps its port, and the next job uses it. Keep this
# script and its parents: they are the runner and the job that runs this hook.
keep=" "
pid=$$
while [ "$pid" -gt 1 ]; do
	keep+="$pid "
	pid=$(ps -o ppid= -p "$pid" | tr -d ' ')
done
for pid in $(pgrep -u runner); do
	case "$keep" in *" $pid "*) ;; *) kill -9 "$pid" 2>/dev/null ;; esac
done

docker rm -f $(docker ps -aq) >/dev/null 2>&1 || true
docker network prune -f >/dev/null
sudo rm -rf /home/runner/frappe-bench /data
