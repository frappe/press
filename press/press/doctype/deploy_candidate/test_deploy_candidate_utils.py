# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for deploy_candidate/utils.py and deploy_candidate/validations.py.
Both modules are pure-Python utility layers with no Frappe-document dependencies,
so we can exercise them with plain unittest fixtures (tmp files, in-memory data).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.deploy_candidate.utils import (
	BuildValidationError,
	get_build_server_with_least_active_builds,
	get_error_key,
	get_package_manager_files,
	get_package_manager_files_from_repo,
	is_suspended,
	load_package_json,
	load_pyproject,
)
from press.press.doctype.deploy_candidate.validations import get_required_apps_from_hookpy

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _write(path: Path, content: str) -> Path:
	path.write_text(content)
	return path


# ══════════════════════════════════════════════════════════════════════════════
# validations.get_required_apps_from_hookpy
# ══════════════════════════════════════════════════════════════════════════════


class TestGetRequiredAppsFromHookpy(FrappeTestCase):
	"""get_required_apps_from_hookpy() parses required_apps from hooks.py."""

	def _run(self, hooks_content: str) -> list[str]:
		with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
			f.write(hooks_content)
			path = f.name
		try:
			return get_required_apps_from_hookpy(path)
		finally:
			os.unlink(path)

	def test_returns_required_apps_list(self):
		"""Returns apps listed in required_apps."""
		result = self._run('required_apps = ["frappe", "erpnext"]')
		self.assertEqual(result, ["frappe", "erpnext"])

	def test_returns_empty_list_when_no_required_apps(self):
		"""Returns [] when required_apps is absent from hooks.py."""
		result = self._run("app_name = 'myapp'\napp_version = '1.0.0'\n")
		self.assertEqual(result, [])

	def test_returns_empty_list_for_non_list_required_apps(self):
		"""Returns [] when required_apps is assigned a non-list value."""
		result = self._run("required_apps = 'frappe'")
		self.assertEqual(result, [])

	def test_returns_empty_list_for_empty_list(self):
		"""Returns [] for required_apps = []."""
		result = self._run("required_apps = []")
		self.assertEqual(result, [])

	def test_returns_single_app(self):
		"""Works correctly for a single-element list."""
		result = self._run('required_apps = ["frappe"]')
		self.assertEqual(result, ["frappe"])

	def test_ignores_other_assignments_with_same_structure(self):
		"""Only the required_apps assignment is parsed; others are ignored."""
		hooks = (
			'app_name = "myapp"\nsome_list = ["a", "b"]\nrequired_apps = ["frappe"]\nanother_list = ["x"]\n'
		)
		result = self._run(hooks)
		self.assertEqual(result, ["frappe"])


# ══════════════════════════════════════════════════════════════════════════════
# utils.get_error_key
# ══════════════════════════════════════════════════════════════════════════════


class TestGetErrorKey(FrappeTestCase):
	"""get_error_key() normalises error substrings into stable lookup keys."""

	def test_lowercases_string(self):
		self.assertEqual(get_error_key("SomeError"), "someerror")

	def test_strips_quotes(self):
		result = get_error_key("\"quoted\" 'string'")
		self.assertNotIn('"', result)
		self.assertNotIn("'", result)

	def test_strips_trailing_period(self):
		result = get_error_key("error message.")
		self.assertFalse(result.endswith("."))

	def test_handles_list_input(self):
		"""When given a list, joins with space then normalises."""
		result = get_error_key(["Part", "One"])
		self.assertIn("part", result)
		self.assertIn("one", result)

	def test_strips_brackets_and_colons(self):
		result = get_error_key("[error]: something")
		self.assertNotIn("[", result)
		self.assertNotIn("]", result)
		self.assertNotIn(":", result)

	def test_stable_across_calls(self):
		"""The same input always produces the same output."""
		key1 = get_error_key("pip install failed.")
		key2 = get_error_key("pip install failed.")
		self.assertEqual(key1, key2)


# ══════════════════════════════════════════════════════════════════════════════
# utils.load_package_json
# ══════════════════════════════════════════════════════════════════════════════


class TestLoadPackageJson(FrappeTestCase):
	def setUp(self):
		self.tmp = tempfile.mkdtemp()

	def tearDown(self):
		import shutil

		shutil.rmtree(self.tmp, ignore_errors=True)

	def test_loads_valid_json(self):
		p = Path(self.tmp) / "package.json"
		p.write_bytes(json.dumps({"name": "myapp", "version": "1.0.0"}).encode())
		result = load_package_json("myapp", str(p))
		self.assertEqual(result["name"], "myapp")

	def test_raises_on_invalid_json(self):
		p = Path(self.tmp) / "package.json"
		p.write_bytes(b"not json {{{")
		with self.assertRaises(Exception) as ctx:
			load_package_json("myapp", str(p))
		self.assertIn("invalid package.json", str(ctx.exception).lower())


# ══════════════════════════════════════════════════════════════════════════════
# utils.load_pyproject
# ══════════════════════════════════════════════════════════════════════════════


class TestLoadPyproject(FrappeTestCase):
	def setUp(self):
		self.tmp = tempfile.mkdtemp()

	def tearDown(self):
		import shutil

		shutil.rmtree(self.tmp, ignore_errors=True)

	def test_loads_valid_toml(self):
		p = Path(self.tmp) / "pyproject.toml"
		p.write_bytes(b'[tool.poetry]\nname = "myapp"\nversion = "1.0.0"\n')
		result = load_pyproject("myapp", str(p))
		self.assertEqual(result["tool"]["poetry"]["name"], "myapp")

	def test_raises_on_invalid_toml(self):
		p = Path(self.tmp) / "pyproject.toml"
		p.write_bytes(b"[[[ invalid toml")
		with self.assertRaises(Exception) as ctx:
			load_pyproject("myapp", str(p))
		self.assertIn("invalid pyproject.toml", str(ctx.exception).lower())


# ══════════════════════════════════════════════════════════════════════════════
# utils.get_package_manager_files_from_repo
# ══════════════════════════════════════════════════════════════════════════════


class TestGetPackageManagerFilesFromRepo(FrappeTestCase):
	def setUp(self):
		self.tmp = tempfile.mkdtemp()

	def tearDown(self):
		import shutil

		shutil.rmtree(self.tmp, ignore_errors=True)

	def _repo(self, files: dict[str, str]) -> str:
		"""Create a fake repo with the given file contents."""
		for rel_path, content in files.items():
			full = Path(self.tmp) / rel_path
			full.parent.mkdir(parents=True, exist_ok=True)
			full.write_text(content)
		return self.tmp

	def test_finds_pyproject_toml(self):
		self._repo({"pyproject.toml": '[tool]\nname = "x"\n'})
		result = get_package_manager_files_from_repo("myapp", self.tmp)
		self.assertIsNotNone(result["pyproject"])

	def test_finds_package_json(self):
		self._repo({"package.json": '{"name": "x"}'})
		result = get_package_manager_files_from_repo("myapp", self.tmp)
		self.assertEqual(len(result["packagejsons"]), 1)

	def test_empty_repo_returns_nones(self):
		result = get_package_manager_files_from_repo("myapp", self.tmp)
		self.assertIsNone(result["pyproject"])
		self.assertEqual(result["packagejsons"], [])

	def test_pyproject_inside_subdir_is_found(self):
		self._repo({"subdir/pyproject.toml": '[tool]\nname = "x"\n'})
		result = get_package_manager_files_from_repo("myapp", self.tmp)
		self.assertIsNotNone(result["pyproject"])

	def test_get_package_manager_files_maps_multiple_apps(self):
		"""get_package_manager_files() returns a mapping keyed by app name."""
		self._repo({"package.json": '{"name": "myapp"}'})
		result = get_package_manager_files({"myapp": self.tmp})
		self.assertIn("myapp", result)
		self.assertEqual(len(result["myapp"]["packagejsons"]), 1)


# ══════════════════════════════════════════════════════════════════════════════
# utils.is_suspended
# ══════════════════════════════════════════════════════════════════════════════


class TestIsSuspended(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_returns_false_when_not_suspended(self):
		frappe.db.set_single_value("Press Settings", "suspend_builds", 0)
		self.assertFalse(is_suspended())

	def test_returns_true_when_suspended(self):
		frappe.db.set_single_value("Press Settings", "suspend_builds", 1)
		self.assertTrue(is_suspended())
		# Restore
		frappe.db.set_single_value("Press Settings", "suspend_builds", 0)


# ══════════════════════════════════════════════════════════════════════════════
# utils.get_build_server_with_least_active_builds
# ══════════════════════════════════════════════════════════════════════════════


class TestGetBuildServerWithLeastActiveBuilds(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_returns_none_when_no_build_servers(self):
		with patch("press.press.doctype.deploy_candidate.utils.frappe.get_all", return_value=[]):
			result = get_build_server_with_least_active_builds("x86_64")
		self.assertIsNone(result)

	def test_returns_single_server_directly(self):
		with patch(
			"press.press.doctype.deploy_candidate.utils.frappe.get_all",
			return_value=["build-srv-1"],
		):
			result = get_build_server_with_least_active_builds("x86_64")
		self.assertEqual(result, "build-srv-1")

	def test_returns_server_with_fewest_builds(self):
		"""When multiple servers exist, pick the one with the lowest active build count."""
		servers = ["busy-srv", "idle-srv"]
		build_count = {"busy-srv": 5, "idle-srv": 1}

		with (
			patch(
				"press.press.doctype.deploy_candidate.utils.frappe.get_all",
				return_value=servers,
			),
			patch(
				"press.press.doctype.deploy_candidate.utils.get_active_build_count_by_build_server",
				return_value=build_count,
			),
		):
			result = get_build_server_with_least_active_builds("x86_64")

		self.assertEqual(result, "idle-srv")

	def test_unknown_server_counts_as_zero(self):
		"""A server absent from the build_count dict is treated as having 0 active builds."""
		servers = ["known-srv", "unknown-srv"]
		build_count = {"known-srv": 3}

		with (
			patch(
				"press.press.doctype.deploy_candidate.utils.frappe.get_all",
				return_value=servers,
			),
			patch(
				"press.press.doctype.deploy_candidate.utils.get_active_build_count_by_build_server",
				return_value=build_count,
			),
		):
			result = get_build_server_with_least_active_builds("x86_64")

		self.assertEqual(result, "unknown-srv")


# ══════════════════════════════════════════════════════════════════════════════
# utils.BuildValidationError
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildValidationError(FrappeTestCase):
	def test_is_subclass_of_validation_error(self):
		self.assertTrue(issubclass(BuildValidationError, frappe.ValidationError))

	def test_can_be_raised_and_caught(self):
		with self.assertRaises(BuildValidationError):
			raise BuildValidationError("test error")
