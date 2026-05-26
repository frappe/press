# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from __future__ import annotations

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app_release_approval_request.app_release_approval_request import (
	AppReleaseApprovalRequest,
)


def _make_approval_request(marketplace_app: str, app_release: str) -> AppReleaseApprovalRequest:
	"""Insert an AppReleaseApprovalRequest bypassing after_insert hooks."""
	with patch.object(AppReleaseApprovalRequest, "after_insert", new=MagicMock()):
		return frappe.get_doc(
			{
				"doctype": "App Release Approval Request",
				"marketplace_app": marketplace_app,
				"app_release": app_release,
			}
		).insert(ignore_permissions=True)


def _make_app_release(status: str = "Draft") -> tuple[str, str, str]:
	"""Create minimal marketplace + app release fixtures.

	Returns (marketplace_app_name, app_release_name, team_name).
	"""
	from press.press.doctype.app.test_app import create_test_app
	from press.press.doctype.app_release.test_app_release import create_test_app_release
	from press.press.doctype.app_source.test_app_source import create_test_app_source
	from press.press.doctype.team.test_team import create_test_team

	team = create_test_team()

	app = create_test_app()
	source = create_test_app_source("Version 14", app, team=team.name)
	release = create_test_app_release(source)
	release.db_set("status", status)

	# Create a minimal Marketplace App linked to the real team
	mp_app = frappe.get_doc(
		{
			"doctype": "Marketplace App",
			"app": app.name,
			"title": app.title,
			"team": team.name,
			"route": app.name,
		}
	).insert(ignore_permissions=True, ignore_links=True)

	return mp_app.name, release.name, team.name


# ═════════════════════════════════════════════════════════════════
# 1. Approval Request Guard Conditions
# ═════════════════════════════════════════════════════════════════


class TestApprovalRequestGuards(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch.object(AppReleaseApprovalRequest, "after_insert", new=MagicMock())
	def test_creating_request_sets_release_to_awaiting_approval(self):
		"""Inserting an AppReleaseApprovalRequest must flip the release status
		to 'Awaiting Approval' via update_release_status()."""
		mp_app, release_name, _ = _make_app_release()
		_make_approval_request(mp_app, release_name)
		status = frappe.db.get_value("App Release", release_name, "status")
		self.assertEqual(status, "Awaiting Approval")

	@patch.object(AppReleaseApprovalRequest, "after_insert", new=MagicMock())
	def test_duplicate_request_for_same_release_raises(self):
		"""A second active request for the same release must raise a validation error."""
		mp_app, release_name, _ = _make_app_release()
		_make_approval_request(mp_app, release_name)
		with self.assertRaises(frappe.ValidationError):
			_make_approval_request(mp_app, release_name)

	@patch.object(AppReleaseApprovalRequest, "after_insert", new=MagicMock())
	def test_request_for_yanked_release_raises(self):
		"""Creating a request for a Yanked release must be blocked."""
		mp_app, release_name, _ = _make_app_release(status="Yanked")
		with self.assertRaises(frappe.ValidationError):
			_make_approval_request(mp_app, release_name)

	@patch.object(AppReleaseApprovalRequest, "after_insert", new=MagicMock())
	def test_another_open_request_from_same_source_raises(self):
		"""When an open request already exists for the same source (different release),
		submitting another must raise a validation error."""
		from press.press.doctype.app.test_app import create_test_app
		from press.press.doctype.app_release.test_app_release import create_test_app_release
		from press.press.doctype.app_source.test_app_source import create_test_app_source
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		app = create_test_app()
		source = create_test_app_source("Version 14", app, team=team.name)

		release1 = create_test_app_release(source)
		release2 = create_test_app_release(source)

		mp_app = frappe.get_doc(
			{
				"doctype": "Marketplace App",
				"app": app.name,
				"title": app.title,
				"team": team.name,
				"route": app.name,
			}
		).insert(ignore_permissions=True, ignore_links=True)

		# First request — OK
		_make_approval_request(mp_app.name, release1.name)

		# Second request from the same source — must fail
		with self.assertRaises(frappe.ValidationError):
			_make_approval_request(mp_app.name, release2.name)


# ═════════════════════════════════════════════════════════════════
# 2. Approval Request Status Propagation (on_update)
# ═════════════════════════════════════════════════════════════════


class TestApprovalRequestStatusPropagation(FrappeTestCase):
	def setUp(self):
		self.mp_app, self.release_name, self.team_name = _make_app_release()

	def tearDown(self):
		frappe.db.rollback()

	def _create_request(self) -> AppReleaseApprovalRequest:
		with patch.object(AppReleaseApprovalRequest, "after_insert", new=MagicMock()):
			return frappe.get_doc(
				{
					"doctype": "App Release Approval Request",
					"marketplace_app": self.mp_app,
					"app_release": self.release_name,
				}
			).insert(ignore_permissions=True)

	@patch.object(AppReleaseApprovalRequest, "notify_publisher", new=MagicMock())
	def test_approved_request_sets_release_to_approved(self):
		"""When status changes to 'Approved', the linked release must become 'Approved'."""
		req = self._create_request()
		# Bypass validate_audit_for_approval
		with patch.object(AppReleaseApprovalRequest, "validate_audit_for_approval", new=MagicMock()):
			req.status = "Approved"
			req.save(ignore_permissions=True)
		status = frappe.db.get_value("App Release", self.release_name, "status")
		self.assertEqual(status, "Approved")

	@patch.object(AppReleaseApprovalRequest, "notify_publisher", new=MagicMock())
	def test_rejected_request_sets_release_to_rejected(self):
		"""When status changes to 'Rejected', the linked release must become 'Rejected'."""
		req = self._create_request()
		req.status = "Rejected"
		req.save(ignore_permissions=True)
		status = frappe.db.get_value("App Release", self.release_name, "status")
		self.assertEqual(status, "Rejected")

	def test_cancelled_request_sets_release_to_draft(self):
		"""Cancelling a request must revert the release to 'Draft'."""
		req = self._create_request()
		req.cancel()
		status = frappe.db.get_value("App Release", self.release_name, "status")
		self.assertEqual(status, "Draft")


# ═════════════════════════════════════════════════════════════════
# 3. Auto-Approval via before_save
# ═════════════════════════════════════════════════════════════════


class TestApprovalRequestAutoApproval(FrappeTestCase):
	def setUp(self):
		self.mp_app, self.release_name, self.team_name = _make_app_release()

	def tearDown(self):
		frappe.db.rollback()

	def _build_request_doc(self) -> AppReleaseApprovalRequest:
		"""Build an unsaved request doc to call before_save() on."""
		doc = frappe.new_doc("App Release Approval Request")
		doc.marketplace_app = self.mp_app
		doc.app_release = self.release_name
		doc.team = self.team_name
		doc.status = "Open"
		return doc

	def test_featured_app_request_is_auto_approved(self):
		"""A request for a featured Marketplace App must be auto-approved in before_save."""
		doc = self._build_request_doc()
		with patch(
			"frappe.get_all",
			side_effect=lambda dt, filters=None, pluck=None, **kw: (
				[self.mp_app] if dt == "Featured App" else []
			),
		):
			doc.before_save()
		self.assertEqual(doc.status, "Approved")

	def test_auto_release_team_request_is_auto_approved(self):
		"""A request from an Auto Release Team must be auto-approved in before_save."""
		doc = self._build_request_doc()
		with patch(
			"frappe.get_all",
			side_effect=lambda dt, filters=None, pluck=None, **kw: (
				[] if dt == "Featured App" else [self.team_name]
			),
		):
			doc.before_save()
		self.assertEqual(doc.status, "Approved")

	def test_regular_team_non_featured_app_request_stays_open(self):
		"""A regular team + non-featured app must NOT be auto-approved."""
		doc = self._build_request_doc()
		with patch("frappe.get_all", return_value=[]):
			doc.before_save()
		self.assertEqual(doc.status, "Open")
