"""
Local test runner — call with: bench --site test-press.local execute press.run_tests_local.run
"""

import sys
import unittest

import frappe


def run():
	modules = [
		"press.press.doctype.app_release_approval_request.test_app_release_approval_request",
		"press.press.doctype.app_release_difference.test_app_release_difference",
		"press.press.doctype.app_release.test_app_release",
		"press.press.doctype.app_source.test_app_source",
		"press.press.doctype.agent_job.test_agent_job",
		"press.press.doctype.site.test_site",
		"press.press.doctype.team.test_team",
		"press.press.doctype.deploy_candidate_build.test_deploy_candidate_build",
		"press.press.doctype.release_group.test_release_group",
	]

	frappe.set_user("Administrator")
	loader = unittest.TestLoader()
	suite = unittest.TestSuite()

	for mod_path in modules:
		try:
			module = frappe.get_module(mod_path)
			suite.addTests(loader.loadTestsFromModule(module))
			print(f"✓ Loaded {mod_path}", flush=True)
		except Exception as e:
			print(f"✗ LOAD ERROR {mod_path}: {e}", flush=True)

	runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
	result = runner.run(suite)

	print(f"\n{'=' * 60}", flush=True)
	print(
		f"Ran {result.testsRun} tests | {len(result.failures)} failures | {len(result.errors)} errors",
		flush=True,
	)
	if result.failures:
		print("\nFAILURES:", flush=True)
		for test, tb in result.failures:
			print(f"  FAIL: {test}", flush=True)
			print(tb[-500:], flush=True)
	if result.errors:
		print("\nERRORS:", flush=True)
		for test, tb in result.errors:
			print(f"  ERROR: {test}", flush=True)
			print(tb[-500:], flush=True)
