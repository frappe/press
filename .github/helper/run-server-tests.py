"""Runs frappe's CLI like `bench` does, with the test files split by run time.

frappe splits the files into contiguous chunks with the same number of tests,
so one shard ran for about a minute longer than another. Usage, from sites/:

    ../env/bin/python run-server-tests.py frappe --site <site> run-parallel-tests ...
"""

import json
import os
from pathlib import Path

from frappe import get_app_path
from frappe.parallel_test_runner import ParallelTestRunner, get_all_tests
from frappe.utils.bench_helper import main

# Seconds per test function in a file without a measured time. About the mean
# of the files in test-durations.json.
SECONDS_PER_TEST = 0.5

DURATIONS = json.loads(Path(__file__).with_name("test-durations.json").read_text())


def module_name(app: str, test: list[str]) -> str:
	path, filename = test
	relative = os.path.relpath(os.path.join(path, filename), os.path.dirname(get_app_path(app)))
	return relative.removesuffix(".py").replace(os.sep, ".")


def duration(app: str, test: list[str]) -> float:
	return (
		DURATIONS.get(module_name(app, test)) or ParallelTestRunner.get_test_weight(test) * SECONDS_PER_TEST
	)


def split_by_duration(app: str, tests: list[list[str]], count: int) -> list[list[list[str]]]:
	"""Give each file, longest first, to the shard with the least work. Keep the file order in a shard."""
	loads = [0.0] * count
	shard_of = {}
	for test in sorted(tests, key=lambda test: duration(app, test), reverse=True):
		shard = loads.index(min(loads))
		loads[shard] += duration(app, test)
		shard_of[tuple(test)] = shard
	return [[test for test in tests if shard_of[tuple(test)] == shard] for shard in range(count)]


def get_test_file_list(self) -> list[list[str]]:
	shards = split_by_duration(self.app, get_all_tests(self.app), self.total_builds)
	return shards[self.build_number - 1]


ParallelTestRunner.get_test_file_list = get_test_file_list
main()
