#!/bin/sh
# Weekly cron job on the runner VM: /etc/cron.weekly/runner-prune (README.md).
# Stops the runners, removes the Docker data that no runner uses and the shared
# caches, then starts the runners again. The runners keep their registration.
cd /opt/runner || exit 1

# Wait up to 30 minutes for the jobs that are running to finish.
# ponytail: a job that starts after this check is stopped with the runner.
for i in $(seq 60); do
	busy=0
	for c in $(docker compose ps -q); do
		docker exec "$c" pgrep -f Runner.Worker >/dev/null && busy=1
	done
	[ "$busy" = 0 ] && break
	sleep 30
done

docker compose stop
docker volume prune -f
docker image prune -f
docker builder prune -af
# Nothing writes to the caches while the runners are stopped. runner.sh makes
# the directories again when the runners start. The pip and yarn caches are
# cleared once a month, on the first Sunday.
rm -rf /opt/runner-cache/runs
if [ "$(date +%d)" -le 7 ]; then
	rm -rf /opt/runner-cache/pip /opt/runner-cache/yarn
fi
docker compose start
