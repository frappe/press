# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import json
import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests import UnitTestCase

from press.marketplace.doctype.marketplace_app_audit.checks.compatibility import (
	_get_supported_frappe_versions,
	_safe_load_pyproject,
	check_bench_compatibility,
	run_compatibility_checks,
)
from press.marketplace.doctype.marketplace_app_audit.checks.semgrep_rules import (
	SEMGREP_TO_AUDIT_SEVERITY,
	_build_category_results,
	_highest_audit_severity,
	_parse_semgrep_errors,
	_serialize_finding,
)
from press.marketplace.doctype.marketplace_app_audit.marketplace_app_audit import (
	CheckResult,
	MarketplaceAppAudit,
)
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release_approval_request.app_release_approval_request import (
	AppReleaseApprovalRequest,
)
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.marketplace_app.test_marketplace_app import create_test_marketplace_app
from press.press.doctype.team.test_team import create_test_team


@patch.object(MarketplaceAppAudit, "trigger_audit", new=Mock())
class TestMarketplaceAppAudit(UnitTestCase):
	"""Basic flow: audit creation from release, run_audit, overall result, approval & publish gates."""

	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.app = create_test_app("marketplace_audit_app", "Marketplace Audit App")
		self.source = self.create_test_source(self.app, self.team.name)
		self.marketplace_app = create_test_marketplace_app(
			self.app.name,
			self.team.name,
			sources=[{"version": "Version 15", "source": self.source.name}],
		)

	def tearDown(self):
		frappe.db.rollback()

	def create_test_source(self, app, team):
		"""Create an app source without auto-creating a release during setup."""
		with patch.object(AppSource, "create_release", return_value=None):
			return app.add_source(
				repository_url="https://github.com/frappe/erpnext",
				branch="master",
				frappe_version="Version 15",
				team=team,
			)

	def create_release(self, source, status: str = "Draft", hash_value: str | None = None):
		return frappe.get_doc(
			{
				"doctype": "App Release",
				"app": source.app,
				"source": source.name,
				"team": source.team,
				"hash": hash_value or frappe.generate_hash(length=40),
				"message": "Test Msg",
				"author": "Test Author",
				"status": status,
			}
		).insert()

	def create_audit_doc(
		self,
		app_release: str,
		status: str = "Completed",
		result: str = "Pass",
		audit_summary: str = "Audit summary",
	) -> MarketplaceAppAudit:
		return frappe.get_doc(
			{
				"doctype": "Marketplace App Audit",
				"marketplace_app": self.marketplace_app.name,
				"app_release": app_release,
				"audit_type": "Manual Run",
				"status": status,
				"audit_result": result,
				"audit_summary": audit_summary,
				"team": self.team.name,
			}
		).insert()

	def create_approval_request(self, app_release: str):
		AppReleaseApprovalRequest.create(self.marketplace_app.name, app_release)
		return frappe.get_last_doc("App Release Approval Request", {"app_release": app_release})

	def test_marketplace_release_creates_audit(self):
		audits_before = frappe.db.count("Marketplace App Audit")
		release = self.create_release(self.source, hash_value="marketplace-release-with-audit")
		self.assertEqual(frappe.db.count("Marketplace App Audit"), audits_before + 1)

		audit = frappe.get_last_doc("Marketplace App Audit", {"app_release": release.name})
		self.assertEqual(audit.marketplace_app, self.marketplace_app.name)
		self.assertEqual(audit.team, self.team.name)
		self.assertEqual(audit.status, "Queued")
		self.assertEqual(audit.audit_type, "Release Change")

	def test_create_for_release_sets_fields(self):
		release = self.create_release(self.source)
		MarketplaceAppAudit.create_for_release(
			marketplace_app=self.marketplace_app.name,
			app_release=release.name,
			audit_type="Manual Run",
		)
		audit = frappe.get_last_doc("Marketplace App Audit", {"app_release": release.name})
		self.assertEqual(audit.marketplace_app, self.marketplace_app.name)
		self.assertEqual(audit.app_release, release.name)
		self.assertEqual(audit.team, self.team.name)
		self.assertEqual(audit.audit_type, "Manual Run")
		self.assertEqual(audit.status, "Queued")
		MarketplaceAppAudit.trigger_audit.assert_called()

	def test_run_audit_success_populates_checks_and_summary(self):
		release = self.create_release(self.source)
		audit = self.create_audit_doc(release.name, status="Queued", result="Inconclusive", audit_summary="")
		results = [
			CheckResult(
				check_id="meta_example",
				check_name="Example Metadata Check",
				category="Metadata",
				result="Pass",
				severity="Major",
				message="Looks good.",
			)
		]
		with patch.object(MarketplaceAppAudit, "execute_audit_checks", return_value=results):
			audit.run_audit()
		audit.reload()
		self.assertEqual(audit.status, "Completed")
		self.assertEqual(audit.audit_result, "Pass")
		self.assertEqual(len(audit.audit_checks), 1)
		self.assertIn("checks run", audit.audit_summary or "")
		self.assertIsNotNone(audit.finished_at)

	def test_run_audit_failure_marks_failed(self):
		release = self.create_release(self.source)
		audit = self.create_audit_doc(release.name, status="Queued")
		with patch.object(
			MarketplaceAppAudit, "execute_audit_checks", side_effect=RuntimeError("clone failed")
		):
			audit.run_audit()
		audit.reload()
		self.assertEqual(audit.status, "Failed")
		self.assertEqual(audit.audit_result, "Inconclusive")
		self.assertIn("unexpected error", (audit.audit_summary or "").lower())
		self.assertTrue(audit.error_traceback)

	def test_overall_result_fail_on_critical_check_failure(self):
		release = self.create_release(self.source)
		audit = self.create_audit_doc(release.name, status="Queued")
		results = [
			CheckResult(
				check_id="crit",
				check_name="Critical",
				category="Dependencies",
				result="Fail",
				severity="Critical",
				message="gate",
			),
		]
		with patch.object(MarketplaceAppAudit, "execute_audit_checks", return_value=results):
			audit.run_audit()
		audit.reload()
		self.assertEqual(audit.audit_result, "Fail")

	def test_approval_blocked_when_audit_fails(self):
		release = self.create_release(self.source)
		self.create_audit_doc(
			release.name,
			status="Completed",
			result="Fail",
			audit_summary="Critical checks failed.",
		)
		request = self.create_approval_request(release.name)
		with self.assertRaises(frappe.ValidationError):
			request.status = "Approved"
			request.save(ignore_permissions=True)

	def test_publish_allowed_with_approved_release_and_acceptable_audit(self):
		with self.assertRaises(frappe.ValidationError):
			self.marketplace_app.status = "Published"
			self.marketplace_app.save(ignore_permissions=True)

		release = self.create_release(self.source, status="Approved")
		self.create_audit_doc(
			release.name,
			status="Completed",
			result="Needs Improvement",
			audit_summary="Only minor issues remain.",
		)
		self.marketplace_app.reload()
		self.marketplace_app.status = "Published"
		self.marketplace_app.save(ignore_permissions=True)
		self.assertEqual(self.marketplace_app.status, "Published")


class TestSemgrepRulesParsing(UnitTestCase):
	"""Tests for semgrep output parsing — no semgrep binary needed."""

	def _make_finding(self, rule_id: str, category: str = "Security", severity: str = "ERROR"):
		return {
			"check_id": f"rules.security.{rule_id}",
			"path": "app/api.py",
			"start": {"line": 10, "col": 1, "offset": 100},
			"end": {"line": 10, "col": 30, "offset": 130},
			"extra": {
				"severity": severity,
				"message": f"Found {rule_id} issue.",
				"metadata": {"marketplace_category": category},
			},
		}

	def test_no_findings_produces_pass_for_each_category(self):
		results = _build_category_results([])
		self.assertEqual(len(results), 2)  # Correctness + Security
		self.assertTrue(all(r.result == "Pass" for r in results))

	def test_security_finding_produces_fail(self):
		findings = [self._make_finding("frappe-codeinjection-eval")]
		results = _build_category_results(findings)
		security = next(r for r in results if r.category == "Security")
		self.assertEqual(security.result, "Fail")
		self.assertIn("1 issue", security.message)

	def test_multiple_findings_aggregated_per_category(self):
		findings = [
			self._make_finding("frappe-codeinjection-eval"),
			self._make_finding("frappe-sql-format-injection"),
		]
		results = _build_category_results(findings)
		security = next(r for r in results if r.category == "Security")
		details = json.loads(security.details)
		self.assertEqual(len(details["occurrences"]), 2)

	def test_highest_severity_is_picked(self):
		findings = [
			self._make_finding("low-rule", severity="WARNING"),
			self._make_finding("high-rule", severity="ERROR"),
		]
		self.assertEqual(_highest_audit_severity(findings), "Critical")

	def test_warning_severity_produces_warn_result(self):
		findings = [self._make_finding("minor-rule", severity="WARNING")]
		results = _build_category_results(findings)
		security = next(r for r in results if r.category == "Security")
		self.assertEqual(security.result, "Warn")
		self.assertEqual(security.severity, "Minor")

	def test_serialize_finding_extracts_short_rule_id(self):
		finding = self._make_finding("frappe-codeinjection-eval")
		serialized = _serialize_finding(finding)
		self.assertEqual(serialized["rule_id"], "frappe-codeinjection-eval")
		self.assertEqual(serialized["path"], "app/api.py")

	def test_parse_semgrep_errors(self):
		errors = [{"message": "Rule parse error"}, {"message": "Timeout on file"}]
		results = _parse_semgrep_errors(errors)
		self.assertEqual(len(results), 2)
		self.assertTrue(all(r.result == "Error" for r in results))

	def test_severity_mapping_covers_all_levels(self):
		self.assertEqual(SEMGREP_TO_AUDIT_SEVERITY["ERROR"], "Critical")
		self.assertEqual(SEMGREP_TO_AUDIT_SEVERITY["WARNING"], "Minor")
		self.assertEqual(SEMGREP_TO_AUDIT_SEVERITY["INFO"], "Info")

	def test_unknown_category_finding_is_ignored(self):
		findings = [self._make_finding("unknown-rule", category="UnknownCategory")]
		results = _build_category_results(findings)
		# Both expected categories should pass since the finding doesn't belong to either
		self.assertTrue(all(r.result == "Pass" for r in results))


class TestCompatibilityChecks(UnitTestCase):
	"""Tests for compatibility check logic — uses mocks for DB queries."""

	def test_safe_load_pyproject_returns_none_for_missing_file(self):
		self.assertIsNone(_safe_load_pyproject("/nonexistent/pyproject.toml"))

	def test_safe_load_pyproject_returns_none_for_invalid_toml(self):
		with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w") as f:
			f.write("this is [[[ not valid toml")
			f.flush()
			self.assertIsNone(_safe_load_pyproject(f.name))
		os.unlink(f.name)

	def test_safe_load_pyproject_parses_valid_toml(self):
		with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w") as f:
			f.write('[tool.bench.frappe-dependencies]\nfrappe = ">=15.0.0,<16.0.0-dev"\n')
			f.flush()
			result = _safe_load_pyproject(f.name)
		os.unlink(f.name)
		self.assertIsNotNone(result)
		self.assertEqual(
			result["tool"]["bench"]["frappe-dependencies"]["frappe"],
			">=15.0.0,<16.0.0-dev",
		)

	def test_run_compatibility_checks_skips_when_no_pyproject(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			results = run_compatibility_checks("SRC-001", tmpdir)
		self.assertEqual(results, [])

	def test_run_compatibility_checks_skips_when_no_frappe_dep(self):
		with tempfile.TemporaryDirectory() as tmpdir:
			with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
				f.write("[tool.bench]\nname = 'myapp'\n")
			results = run_compatibility_checks("SRC-001", tmpdir)
		self.assertEqual(results, [])

	def test_get_supported_frappe_versions_includes_nightly_for_future_upper_bound(self):
		frappe_versions = [
			{"name": "Version 15", "number": 15, "status": "Stable"},
			{"name": "Version 16", "number": 16, "status": "Stable"},
			{"name": "Nightly", "number": 17, "status": "Nightly"},
		]
		with patch(
			"press.marketplace.doctype.marketplace_app_audit.checks.compatibility.frappe.get_all",
			return_value=frappe_versions,
		):
			supported = _get_supported_frappe_versions(">=16.0.0-dev,<=17.0.0-dev")

		self.assertEqual(set(supported or []), {"Version 16", "Nightly"})

	def test_get_supported_frappe_versions_excludes_nightly_for_closed_stable_range(self):
		frappe_versions = [
			{"name": "Version 15", "number": 15, "status": "Stable"},
			{"name": "Version 16", "number": 16, "status": "Stable"},
			{"name": "Nightly", "number": 17, "status": "Nightly"},
		]
		with patch(
			"press.marketplace.doctype.marketplace_app_audit.checks.compatibility.frappe.get_all",
			return_value=frappe_versions,
		):
			supported = _get_supported_frappe_versions(">=15.0.0,<16.0.0")

		self.assertEqual(set(supported or []), {"Version 15"})

	def _patch_qb(self, run_return_value):
		"""Patch frappe.qb with a plain MagicMock (avoids AsyncMock coroutine issues)."""
		mock_qb = MagicMock()
		chain = mock_qb.from_.return_value.join.return_value.on.return_value
		chain.where.return_value.where.return_value.where.return_value.select.return_value.run.return_value = run_return_value
		return patch(
			"press.marketplace.doctype.marketplace_app_audit.checks.compatibility.frappe.qb",
			mock_qb,
		)

	def test_check_bench_compatibility_pass_when_all_compatible(self):
		"""When no incompatible benches exist, result should be Pass."""
		with self._patch_qb([]):
			result = check_bench_compatibility("SRC-001", ["Version 15", "Version 16"], ">=15.0.0")

		self.assertEqual(result.result, "Pass")
		self.assertEqual(result.check_id, "compat_bench_versions")
		self.assertEqual(result.severity, "Critical")

	def test_check_bench_compatibility_fail_when_incompatible_benches(self):
		"""When benches on unsupported versions exist, result should be Fail."""
		incompatible_bench = frappe._dict(name="RG-001", version="Version 14", public=True)

		with self._patch_qb([incompatible_bench]):
			result = check_bench_compatibility("SRC-001", ["Version 15"], ">=15.0.0,<16.0.0-dev")

		self.assertEqual(result.result, "Fail")
		self.assertEqual(result.severity, "Critical")
		details = json.loads(result.details)
		self.assertIn("Version 14", details["incompatible_versions"])
		self.assertEqual(details["public_benches_affected"], 1)

	def test_check_bench_compatibility_reports_both_public_and_private(self):
		incompatible = [
			frappe._dict(name="RG-PUB", version="Version 14", public=True),
			frappe._dict(name="RG-PVT", version="Version 14", public=False),
		]

		with self._patch_qb(incompatible):
			result = check_bench_compatibility("SRC-001", ["Version 16"], ">=16.0.0")

		details = json.loads(result.details)
		self.assertEqual(details["public_benches_affected"], 1)
		self.assertEqual(details["private_benches_affected"], 1)
		self.assertIn("public bench", result.message)
		self.assertIn("private bench", result.message)
