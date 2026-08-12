# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.release_group.release_group import can_run_patch_build
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench


def _setup(apps=None, public=False):
	"""Create release group + active bench, set intel_build on the candidate."""
	if apps is None:
		apps = [create_test_app()]
	rg = create_test_release_group(apps, public=public)
	bench = create_test_bench(group=rg)
	frappe.db.set_value("Deploy Candidate", bench.candidate, "intel_build", bench.build)
	frappe.db.set_single_value("Press Settings", "allow_patch_builds", 1)
	return rg, bench


def _add_arm_build(rg, bench, create_bench=True):
	"""Attach an arm DCB to the candidate and optionally create an active arm bench."""
	arm_dcb = frappe.get_doc(
		{
			"doctype": "Deploy Candidate Build",
			"deploy_candidate": bench.candidate,
			"group": rg.name,
			"run_build": 0,
			"status": "Success",
			"platform": "arm64",
		}
	).insert()
	frappe.db.set_value("Deploy Candidate", bench.candidate, "arm_build", arm_dcb.name)
	if not create_bench:
		return arm_dcb
	return frappe.get_doc(
		{
			"doctype": "Bench",
			"name": f"Test ARM Bench {frappe.generate_hash(length=8)}",
			"status": "Active",
			"background_workers": 1,
			"gunicorn_workers": 2,
			"group": rg.name,
			"candidate": bench.candidate,
			"build": arm_dcb.name,
			"server": bench.server,
			"docker_image": frappe.mock("url"),
		}
	).insert()


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestCanRunPatchBuild(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_returns_true_when_state_matches(self):
		rg, _ = _setup()
		self.assertTrue(can_run_patch_build(rg.name))

	def test_returns_false_when_no_active_bench(self):
		rg = create_test_release_group([create_test_app()])
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_bench_archived(self):
		rg, bench = _setup()
		bench.db_set("status", "Archived")
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_app_added(self):
		rg, _ = _setup()
		new_app = create_test_app("erpnext", "ERPNext")
		new_source = create_test_app_source(rg.version, new_app)
		rg.append("apps", {"app": new_app.name, "source": new_source.name})
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_app_removed(self):
		app1 = create_test_app()
		app2 = create_test_app("erpnext", "ERPNext")
		rg, _ = _setup(apps=[app1, app2])
		rg.apps = [row for row in rg.apps if row.app != app2.name]
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_app_source_changed(self):
		app = create_test_app()
		rg, _ = _setup(apps=[app])
		new_source = create_test_app_source(rg.version, app, branch="develop")
		rg.apps[0].source = new_source.name
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_for_public_group(self):
		rg, _ = _setup()
		rg.db_set("public", 1)
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_dependency_version_changed(self):
		rg, _ = _setup()
		rg.dependencies[0].version = "99.99"
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_dependency_added(self):
		rg, _ = _setup()
		rg.append("dependencies", {"dependency": "WKHTMLTOPDF_VERSION", "version": "0.12.6"})
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_package_added(self):
		rg, _ = _setup()
		rg.append("packages", {"package_manager": "apt", "package": "libmagic1"})
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_package_removed(self):
		app = create_test_app()
		rg = create_test_release_group([app])
		rg.append("packages", {"package_manager": "apt", "package": "libmagic1"})
		rg.save()
		bench = create_test_bench(group=rg)
		frappe.db.set_value("Deploy Candidate", bench.candidate, "intel_build", bench.build)
		rg.packages = []
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_env_var_added(self):
		rg, _ = _setup()
		rg.append("environment_variables", {"key": "MY_VAR", "value": "foo", "internal": 0})
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_env_var_removed(self):
		app = create_test_app()
		rg = create_test_release_group([app])
		rg.append("environment_variables", {"key": "MY_VAR", "value": "foo", "internal": 0})
		rg.save()
		bench = create_test_bench(group=rg)
		frappe.db.set_value("Deploy Candidate", bench.candidate, "intel_build", bench.build)
		rg.environment_variables = []
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_env_var_value_changed(self):
		app = create_test_app()
		rg = create_test_release_group([app])
		rg.append("environment_variables", {"key": "MY_VAR", "value": "foo", "internal": 0})
		rg.save()
		bench = create_test_bench(group=rg)
		frappe.db.set_value("Deploy Candidate", bench.candidate, "intel_build", bench.build)
		rg.environment_variables[0].value = "bar"
		rg.save()
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_false_when_arm_bench_missing_for_dual_platform_candidate(self):
		rg, bench = _setup()
		_add_arm_build(rg, bench, create_bench=False)
		# candidate has both intel_build + arm_build but no active arm bench
		self.assertFalse(can_run_patch_build(rg.name))

	def test_returns_true_when_both_platform_benches_active(self):
		rg, bench = _setup()
		_add_arm_build(rg, bench, create_bench=True)
		self.assertTrue(can_run_patch_build(rg.name))
