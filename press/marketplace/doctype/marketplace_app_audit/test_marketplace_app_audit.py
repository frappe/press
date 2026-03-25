# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

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
class TestMarketplaceAppAudit(FrappeTestCase):
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
