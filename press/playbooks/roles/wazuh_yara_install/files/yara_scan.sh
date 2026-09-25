#!/bin/bash
# Wazuh active response: scan the file a syscheck event just reported.
# Log only. Nothing here moves, quarantines or deletes a customer's file.

LOG_FILE="/var/ossec/logs/active-responses.log"
YARA_BIN="/usr/bin/yara"
# Pushed by the manager from its shared/default group, so updates need no redeploy
YARA_RULES="/var/ossec/etc/shared/frappe_malware.yar"
MAX_SIZE=$((20 * 1024 * 1024))

log() { echo "wazuh-yara: $1 - $2" >> "$LOG_FILE"; }

read -r INPUT_JSON
SCAN_PATH=$(echo "$INPUT_JSON" | jq -r '.parameters.alert.syscheck.path // empty')

[ -z "$SCAN_PATH" ] && { log ERROR "No syscheck path in active response input"; exit 1; }
[ -f "$SCAN_PATH" ] || exit 0
[ -x "$YARA_BIN" ] || { log ERROR "yara is not installed"; exit 1; }
[ -r "$YARA_RULES" ] || { log ERROR "Ruleset missing at $YARA_RULES"; exit 1; }

# A big file is almost never the webshell we are looking for, and scanning it
# stalls the agent on a server that is already serving customer traffic.
if [ "$(stat -c%s "$SCAN_PATH" 2>/dev/null || echo 0)" -gt "$MAX_SIZE" ]; then
	exit 0
fi

# A ruleset that fails to compile must be loud: silence here means no detection anywhere
MATCHES=$("$YARA_BIN" --no-warnings "$YARA_RULES" "$SCAN_PATH" 2>&1)
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
	log ERROR "yara exited $STATUS: $(echo "$MATCHES" | head -1)"
	exit 1
fi
[ -z "$MATCHES" ] && exit 0

while read -r match; do
	log INFO "Scan result: $match"
done <<< "$MATCHES"
