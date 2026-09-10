# Copyright (c) 2024, Frappe and Contributors
# See license.txt
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.deploy_candidate.deploy_notifications import (
	DOC_URLS,
	BuildValidationError,
	check_if_app_updated,
	get_details,
)


def make_dc(
	app_hash: str,
	dependencies: dict,
	environment_variables: dict,
	other_app_hash: str = "xyz789",
	packages: list[str] | None = None,
):
	return frappe._dict(
		apps=[
			frappe._dict(app="frappe", hash=app_hash, pullable_hash=None, title="Frappe"),
			frappe._dict(app="helpdesk", hash=other_app_hash, pullable_hash=None, title="Helpdesk"),
		],
		dependencies=[frappe._dict(dependency=k, version=v) for k, v in dependencies.items()],
		environment_variables=[frappe._dict(key=k, value=v) for k, v in environment_variables.items()],
		packages=[
			frappe._dict(
				package_manager="apt",
				package=package,
				package_prerequisites="",
				after_install="",
			)
			for package in (packages or ["wkhtmltopdf"])
		],
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

	def test_allows_retry_when_another_apps_hash_changed(self):
		deps = {"python": "3.11"}
		env = {"FOO": "bar"}
		old_build = make_old_build(make_dc("abc123", deps, env, other_app_hash="old111"))
		new_dc = make_dc("abc123", deps, env, other_app_hash="new222")

		check_if_app_updated(old_build, new_dc)  # no raise

	def test_blocks_retry_when_only_environment_variables_changed(self):
		deps = {"python": "3.11"}
		old_build = make_old_build(make_dc("abc123", deps, {"FOO": "bar"}))
		new_dc = make_dc("abc123", deps, {"FOO": "baz"})

		with self.assertRaises(BuildValidationError):
			check_if_app_updated(old_build, new_dc)

	def test_escapes_app_title_in_blocked_retry_message(self):
		deps = {"python": "3.11"}
		env = {"FOO": "bar"}
		old_build = make_old_build(make_dc("abc123", deps, env))
		new_dc = make_dc("abc123", deps, env)
		new_dc.apps[0].title = "<img src=x onerror=alert(1)>"

		with self.assertRaises(BuildValidationError) as raised:
			check_if_app_updated(old_build, new_dc)

		self.assertNotIn("<img", str(raised.exception))

	def test_allows_retry_when_packages_changed(self):
		deps = {"python": "3.11"}
		env = {"FOO": "bar"}
		old_build = make_old_build(make_dc("abc123", deps, env, packages=["wkhtmltopdf"]))
		new_dc = make_dc("abc123", deps, env, packages=["wkhtmltopdf", "libmagic1"])

		check_if_app_updated(old_build, new_dc)  # no raise


UV_FRAPPE_DEPENDENCY_OUTPUT = """
Installing my_app
$ uv pip install --quiet -e /home/frappe/frappe-bench/apps/my_app
  x Failed to resolve dependencies for `frappe` (v15.120.1)
  |-> Package `pypika` was included as a URL dependency.
      URL dependencies must be expressed as direct requirements or constraints.

hint: `frappe` (v15.120.1) was included because `my_app` (v0.0.1) depends on `frappe`
Error occured during app install: uv pip install --quiet -e /home/frappe/frappe-bench/apps/my_app
"""


def make_failed_build(build_output: str):
	failed_step = frappe._dict(stage="Install Apps", step="my_app", stage_slug="apps", step_slug="my_app")
	return frappe._dict(
		build_output=build_output,
		get_first_step=lambda *args: failed_step,
	)


class TestFrappeListedAsDependency(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def get_details(self, build_output: str):
		return get_details(
			deploy_candidate=frappe._dict(),
			deploy_candidate_build=make_failed_build(build_output),
			exc=Exception("Build failed"),
		)

	def test_uv_resolution_failure_names_the_app_that_depends_on_frappe(self):
		details = self.get_details(UV_FRAPPE_DEPENDENCY_OUTPUT)

		self.assertTrue(details["is_actionable"])
		self.assertIn("my_app", details["title"])
		self.assertIn("lists frappe as a Python dependency", details["title"])
		self.assertIn("pyproject.toml", details["message"])
		self.assertEqual(
			details["assistance_url"],
			DOC_URLS["frappe-listed-as-a-python-dependency"],
		)

	def test_uv_hint_is_matched_even_when_wrapped_across_lines(self):
		wrapped = UV_FRAPPE_DEPENDENCY_OUTPUT.replace(
			"was included because `my_app` (v0.0.1) depends on `frappe`",
			"was included\nbecause `my_app` (v0.0.1)\ndepends on `frappe`",
		)

		details = self.get_details(wrapped)

		self.assertTrue(details["is_actionable"])
		self.assertIn("my_app", details["title"])

	def test_falls_back_to_default_message_when_the_app_name_is_missing(self):
		output = "hint: something depends on `frappe` but the app name is not printed"

		details = self.get_details(output)

		self.assertFalse(details["is_actionable"])
		self.assertEqual(details["title"], "Build Failed")
		self.assertEqual(
			details["message"],
			"Image build failed at step <b>Install Apps - my_app</b>.",
		)
		self.assertIsNone(details["assistance_url"])

	def test_app_name_from_build_output_is_escaped_in_the_message(self):
		output = UV_FRAPPE_DEPENDENCY_OUTPUT.replace("`my_app` (v0.0.1)", "`<img src=x>` (v0.0.1)")

		details = self.get_details(output)

		self.assertNotIn("<img", details["message"])
