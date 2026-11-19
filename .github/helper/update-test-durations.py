"""Writes test-durations.json from the Server job logs of earlier CI runs.

Each value is the median number of seconds that a test file took. A file's time
runs from the line that names its first test class to the next file's line.

Usage: python3 update-test-durations.py <run id> [<run id> ...]
"""

import json
import re
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from itertools import pairwise
from pathlib import Path

REPOSITORY = "frappe/press"
TIMESTAMP = re.compile(r"^\ufeff?(\S+Z) ")
CLASS_LINE = re.compile(r"^\ufeff?\S+Z (press(?:\.\w+)+)\.\w+$")
COLOR = re.compile(r"\x1b\[[0-9;]*m")


def gh(*arguments: str) -> str:
	return subprocess.run(["gh", *arguments], check=True, capture_output=True, text=True).stdout


def server_job_ids(run_id: str) -> list[str]:
	query = '.jobs[] | select(.name | startswith("Server")) | .id'
	return gh("api", f"repos/{REPOSITORY}/actions/runs/{run_id}/jobs?per_page=100", "-q", query).split()


def file_durations(log: str) -> dict[str, float]:
	"""Seconds per test file in the Run Tests step of one job log."""
	starts: list[tuple[datetime, str]] = []
	in_step = False
	for line in COLOR.sub("", log).splitlines():
		timestamp = TIMESTAMP.match(line)
		if not timestamp:
			continue
		if "run-parallel-tests" in line:
			in_step = True
		elif in_step and "##[group]Run " in line:
			starts.append((parse_time(timestamp.group(1)), "end of step"))
			break
		if in_step and (class_line := CLASS_LINE.match(line)):
			starts.append((parse_time(timestamp.group(1)), class_line.group(1)))
	durations: dict[str, float] = defaultdict(float)
	for (start, module), (end, _) in pairwise(starts):
		durations[module] += (end - start).total_seconds()
	return durations


def parse_time(timestamp: str) -> datetime:
	"""GitHub writes 7 fractional digits, and Python 3.10 reads at most 6."""
	return datetime.fromisoformat(re.sub(r"(\.\d{1,6})\d*Z$", r"\1+00:00", timestamp))


def main(run_ids: list[str]) -> None:
	samples: dict[str, list[float]] = defaultdict(list)
	for run_id in run_ids:
		for job_id in server_job_ids(run_id):
			log = gh("api", "--allow-escape-sequences", f"repos/{REPOSITORY}/actions/jobs/{job_id}/logs")
			for module, seconds in file_durations(log).items():
				samples[module].append(seconds)
	medians = {module: round(statistics.median(values), 1) for module, values in sorted(samples.items())}
	output = Path(__file__).with_name("test-durations.json")
	output.write_text(json.dumps(medians, indent="\t") + "\n")
	print(f"Wrote {len(medians)} files to {output}")


if __name__ == "__main__":
	main(sys.argv[1:])
