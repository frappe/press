#!/bin/bash
# Replace the runners on one VM with containers of the newest image, one idle
# runner at a time, so that running jobs finish. Run it on your computer after
# `docker compose build` on the VM. gh needs admin access to frappe/press.
#
# Usage: rolling.sh <ssh destination> <RUNNER_PREFIX> [number of runners]
set -euo pipefail

host=$1 prefix=$2 count=${3:-6}
api=repos/frappe/press/actions/runners

vm() { ssh "$host" "$@"; }

while true; do
	new=$(vm 'docker image inspect -f "{{.Id}}" runner-runner')
	old=$(vm "cd /opt/runner && for c in \$(docker compose ps -q); do
		[ \"\$(docker inspect -f '{{.Image}}' \$c)\" = '$new' ] || docker inspect -f '{{slice .Id 0 12}} {{.Name}}' \$c
	done")
	[ -n "$old" ] || break

	runners=$(gh api "$api" --paginate -q '.runners[] | "\(.name) \(.id)"')
	token=$(gh api -X POST "$api/registration-token" -q .token)
	while read -r cid cname; do
		rid=$(awk -v n="$prefix-$cid" '$1 == n { print $2 }' <<<"$runners")
		# Delete the runner first. GitHub refuses (HTTP 422) while the runner
		# has a job, and after the delete the runner takes no new job.
		if [ -n "$rid" ] && ! gh api -X DELETE "$api/$rid" >/dev/null 2>&1; then
			continue
		fi
		printf 'RUNNER_PREFIX=%s\nRUNNER_TOKEN=%s\n' "$prefix" "$token" |
			vm "umask 077; cat > /opt/runner/.env; cd /opt/runner &&
				docker rm -f -v ${cname#/} >/dev/null &&
				docker compose up -d --no-recreate --scale runner=$count >/dev/null 2>&1"
		echo "$(date -u +%T) replaced ${cname#/}"
	done <<<"$old"
	sleep 20
done

echo "$(date -u +%T) all runners use the newest image"
