#!/bin/bash
# Mounts the bench that Setup Bench saved on the runner VM at ~/frappe-bench.
# The saved bench stays read-only, and each job writes to its own directory.
set -euo pipefail

saved=/cache/runs/$GITHUB_RUN_ID
changes=$(mktemp -d "$saved/overlay.XXXXXX")
mkdir -p "$changes/upper" "$changes/work" /home/runner/frappe-bench

# Without redirect_dir, a rename of a saved directory fails with EXDEV.
sudo mount -t overlay overlay \
	-o "lowerdir=$saved/frappe-bench,upperdir=$changes/upper,workdir=$changes/work,redirect_dir=on" \
	/home/runner/frappe-bench
