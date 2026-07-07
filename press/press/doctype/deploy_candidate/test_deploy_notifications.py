# Copyright (c) 2024, Frappe and Contributors
# See license.txt
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.deploy_candidate.deploy_notifications import (
	BuildValidationError,
	check_if_app_updated,
)


def make_dc(app_hash: str, dependencies: dict, environment_variables: dict):
	return frappe._dict(
		apps=[frappe._dict(app="frappe", hash=app_hash, pullable_hash=None, title="Frappe")],
		dependencies=[frappe._dict(dependency=k, version=v) for k, v in dependencies.items()],
		environment_variables=[frappe._dict(key=k, value=v) for k, v in environment_variables.items()],
	)


def make_old_build(candidate):
	return frappe._dict(
		candidate=candidate,
		get_first_step=lambda *args: frappe._dict(stage_slug="apps", step_slug="frappe"),
	)


class TestCheckIfAppUpdated(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_blocks_retry_when_nothing_changed(self):
		deps = {"python": "3.11"}
		env = {"FOO": "bar"}
		old_build = make_old_build(make_dc("abc123", deps, env))
		new_dc = make_dc("abc123", deps, env)

		with self.assertRaises(BuildValidationError):
			check_if_app_updated(old_build, new_dc)

	def test_allows_retry_when_app_hash_changed(self):
		deps = {"python": "3.11"}
		env = {"FOO": "bar"}
		old_build = make_old_build(make_dc("abc123", deps, env))
		new_dc = make_dc("def456", deps, env)

		check_if_app_updated(old_build, new_dc)  # no raise

	def test_allows_retry_when_dependencies_changed(self):
		env = {"FOO": "bar"}
		old_build = make_old_build(make_dc("abc123", {"python": "3.11"}, env))
		new_dc = make_dc("abc123", {"python": "3.12"}, env)

		check_if_app_updated(old_build, new_dc)  # no raise

	def test_blocks_retry_when_only_environment_variables_changed(self):
		deps = {"python": "3.11"}
		old_build = make_old_build(make_dc("abc123", deps, {"FOO": "bar"}))
		new_dc = make_dc("abc123", deps, {"FOO": "baz"})

		with self.assertRaises(BuildValidationError):
			check_if_app_updated(old_build, new_dc)
