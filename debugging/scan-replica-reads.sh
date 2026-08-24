#!/bin/sh
# Scan the apps of a bench for code that can serve a stale read on a site that
# has read_from_replica on.
#
# READ ONLY: find, grep, awk, sort. It writes no file and touches no database.
#
# Run it from the bench directory:
#   curl -sL https://raw.githubusercontent.com/frappe/press/fc-scripts/debugging/scan-replica-reads.sh | sh

[ -d apps ] || { echo "run this from the bench directory" >&2; exit 1; }
STANDARD='apps/(frappe|erpnext)/'   # filtered out of the override sections

echo "== 1. reads the replica (@frappe.read_only) =="
find apps -name '*.py' -not -path '*/node_modules/*' -not -path '*/tests/*' -print0 |
xargs -0 -r awk '
  FNR==1 { pending=0; whitelisted=0 }
  /@frappe\.whitelist/ { whitelisted=1 }
  /@(frappe\.)?read_only\(\)/ { pending=1 }
  /^[[:space:]]*def[[:space:]]/ {
    if (pending) {
      name=$0; sub(/^[[:space:]]*def[[:space:]]+/, "", name); sub(/\(.*/, "", name)
      module=FILENAME; sub(/^apps\/[^\/]+\//, "", module); sub(/\.py$/, "", module); gsub(/\//, ".", module)
      printf "%s\t%s.%s\t%s:%d\n", (whitelisted ? "api     " : "internal"), module, name, FILENAME, FNR
    }
    pending=0; whitelisted=0
  }' | sort -t"$(printf '\t')" -k2

echo
echo "== 2. custom app overrides of the read path (hooks.py) =="
grep -rHn -A20 "^override_whitelisted_methods\|^override_doctype_class\|^permission_query_conditions\|^has_permission" apps/*/*/hooks.py |
  grep '":' | grep -Ev "$STANDARD" | grep -v '#' | sort -u

echo
echo "== 3. custom controller get_list / get_count (virtual doctypes) =="
grep -rHn --include='*.py' "def get_list(\|def get_count(" apps/ | grep -Ev "$STANDARD"

echo
echo "== 4. custom whitelisted methods named like the read API =="
grep -rHn --include='*.py' "^def \(get\|get_list\|get_count\|get_detail\|get_doc\)(" apps/ | grep -Ev "$STANDARD"

echo
echo "== 5. redis doc cache in custom apps (a replica read poisons it) =="
grep -rHn --include='*.py' "get_cached_doc\|get_cached_value" apps/ | grep -Ev "$STANDARD"
