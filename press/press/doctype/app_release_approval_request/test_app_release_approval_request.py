# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_release_approval_request.app_release_approval_request import (
	AppReleaseApprovalRequest,
)
from press.press.doctype.team.test_team import create_test_team


def _create_marketplace_app(app, team):
	return frappe.get_doc(
		{
			"doctype": "Marketplace App",
			"app": app.name,
			"description": "Test marketplace app",
			"team": team.name,
		}
	).insert(ignore_permissions=True, ignore_if_duplicate=True)


def _create_request(marketplace_app, release):
	"""Create an approval request, patching sendmail to avoid SMTP calls."""
	with patch("frappe.sendmail"):
		AppReleaseApprovalRequest.create(marketplace_app.name, release.name)
	return frappe.get_last_doc("App Release Approval Request", {"app_release": release.name})


class TestApprovalRequestGuards(FrappeTestCase):
	"""before_insert guards on AppReleaseApprovalRequest prevent invalid requests.

	Three guards run before insert:
	- Duplicate request for the same release must be blocked (double-submit protection)
	- Another Open request from the same source must be blocked (queue discipline)
	- Yanked releases must be blocked entirely (audit-failed code must not be re-reviewed)
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()
		self.app = create_test_app()
		self.source = create_test_app_source("Version 14", self.app, team=self.team.name)
		self.release = create_test_app_release(self.source)
		self.mapp = _create_marketplace_app(self.app, self.team)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_creating_request_sets_release_to_awaiting_approval(self):
		_create_request(self.mapp, self.release)
		self.release.reload()
		self.assertEqual(self.release.status, "Awaiting Approval")

	def test_duplicate_request_for_same_release_raises(self):
		_create_request(self.mapp, self.release)
		with self.assertRaises(frappe.ValidationError), patch("frappe.sendmail"):
			AppReleaseApprovalRequest.create(self.mapp.name, self.release.name)

	def test_request_for_yanked_release_raises(self):
		frappe.db.set_value("App Release", self.release.name, "status", "Yanked")
		with self.assertRaises(frappe.ValidationError), patch("frappe.sendmail"):
			AppReleaseApprovalRequest.create(self.mapp.name, self.release.name)

	def test_another_open_request_from_same_source_raises(self):
		_create_request(self.mapp, self.release)
		release2 = create_test_app_release(self.source)
		with self.assertRaises(frappe.ValidationError), patch("frappe.sendmail"):
			AppReleaseApprovalRequest.create(self.mapp.name, release2.name)


class TestApprovalRequestStatusPropagation(FrappeTestCase):
	"""on_update propagates request status changes back to the linked App Release.

	If this is broken: Approving leaves the release stuck as "Awaiting Approval" and
	blocks it from Deploy Candidates; Rejecting leaves it non-"Rejected" so new requests
	from the same source are blocked; Cancelling leaves it non-"Draft" so resubmission
	is impossible.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()
		self.app = create_test_app()
		self.source = create_test_app_source("Version 14", self.app, team=self.team.name)
		self.release = create_test_app_release(self.source)
		self.mapp = _create_marketplace_app(self.app, self.team)
		self.request = _create_request(self.mapp, self.release)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_approved_request_sets_release_to_approved(self):
		with patch("frappe.sendmail"), patch("frappe.db.commit"):
			self.request.status = "Approved"
			# bypass audit validation for unit test
			with patch.object(self.request, "validate_audit_for_approval"):
				self.request.save(ignore_permissions=True)
		self.release.reload()
		self.assertEqual(self.release.status, "Approved")

	def test_rejected_request_sets_release_to_rejected(self):
		with patch("frappe.sendmail"), patch("frappe.db.commit"):
			self.request.status = "Rejected"
			self.request.save(ignore_permissions=True)
		self.release.reload()
		self.assertEqual(self.release.status, "Rejected")

	def test_cancelled_request_sets_release_to_draft(self):
		with patch("frappe.db.commit"):
			self.request.status = "Cancelled"
			self.request.save(ignore_permissions=True)
		self.release.reload()
		self.assertEqual(self.release.status, "Draft")


class TestApprovalRequestAutoApproval(FrappeTestCase):
	"""before_save auto-approves requests for featured apps and auto-release teams.

	This mirrors the AppRelease auto-approval but at the request level: a featured
	app or trusted team should never have to wait for manual review.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()
		self.app = create_test_app()
		self.source = create_test_app_source("Version 14", self.app, team=self.team.name)
		self.release = create_test_app_release(self.source)
		self.mapp = _create_marketplace_app(self.app, self.team)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_featured_app_request_is_auto_approved(self):
		ms = frappe.get_single("Marketplace Settings")
		ms.append("featured_apps", {"app": self.app.name})
		ms.save(ignore_permissions=True)

		request = _create_request(self.mapp, self.release)
		self.assertEqual(request.status, "Approved")

	def test_auto_release_team_request_is_auto_approved(self):
		ms = frappe.get_single("Marketplace Settings")
		ms.append("auto_release_teams", {"team": self.team.name})
		ms.save(ignore_permissions=True)

		request = _create_request(self.mapp, self.release)
		self.assertEqual(request.status, "Approved")

	def test_regular_team_non_featured_app_request_stays_open(self):
		request = _create_request(self.mapp, self.release)
		self.assertEqual(request.status, "Open")
