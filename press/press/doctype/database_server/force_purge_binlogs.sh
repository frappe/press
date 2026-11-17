#!/usr/bin/env bash
# Deletes the oldest binlogs when a full disk stops MariaDB. Usage: bash -s -- <number of binlogs>
set -euo pipefail

BINLOG_DIR="${BINLOG_DIR:-/var/lib/mysql}"
INDEX_FILE="$BINLOG_DIR/mysql-bin.index"
DELETE_N="${1:-0}"

[ "$DELETE_N" -gt 0 ] || exit 0
trap 'rm -f "$INDEX_FILE.tmp"' EXIT

mapfile -t BINLOGS < <(find "$BINLOG_DIR" -maxdepth 1 -name 'mysql-bin.[0-9]*' -printf '%f\n' | sort -V)
[ "${#BINLOGS[@]}" -gt 0 ] || { echo "No binlogs found. Nothing to purge." >&2; exit 1; }

# Crash recovery reads from the last checkpoint up to the newest binlog, so those binlogs stay
NEWEST="${BINLOGS[-1]}"
CHECKPOINT=$(timeout 60 mysqlbinlog "$BINLOG_DIR/$NEWEST" 2>/dev/null | awk '/Binlog checkpoint/ { checkpoint = $NF } END { print checkpoint }' || true)
DELETABLE=$((${#BINLOGS[@]} - 2))
for index in "${!BINLOGS[@]}"; do
	if [ "${BINLOGS[$index]}" = "$CHECKPOINT" ]; then
		DELETABLE=$index
	fi
done
if [ "$DELETABLE" -lt 1 ]; then
	echo "Only the binlogs that crash recovery needs are left. Nothing to purge." >&2
	exit 1
fi
if [ "$DELETE_N" -gt "$DELETABLE" ]; then
	DELETE_N="$DELETABLE"
fi
TO_DELETE=("${BINLOGS[@]:0:$DELETE_N}")

# Update the index before the delete: MariaDB does not start if the index lists a missing file
if [ -f "$INDEX_FILE" ]; then
	awk 'NR == FNR { deleted[$0]; next } { name = $0; sub(".*/", "", name) } !(name in deleted)' \
		<(printf '%s\n' "${TO_DELETE[@]}") "$INDEX_FILE" >"$INDEX_FILE.tmp"
	chown --reference="$INDEX_FILE" "$INDEX_FILE.tmp"
	chmod --reference="$INDEX_FILE" "$INDEX_FILE.tmp"
	mv "$INDEX_FILE.tmp" "$INDEX_FILE"
fi

for name in "${TO_DELETE[@]}"; do
	rm -f "$BINLOG_DIR/$name"
done

# MariaDB can be stuck on the full disk
systemctl restart mariadb
