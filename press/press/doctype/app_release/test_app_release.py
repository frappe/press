# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app_release.app_release import AppRelease

if typing.TYPE_CHECKING:
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.app_source.app_source import AppSource


def create_test_app_release(app_source: AppSource, hash: str | None = None) -> "AppRelease":
	"""Create test app release given App source."""
	hash = hash or frappe.mock("sha1")
	app_release = frappe.get_doc(
		{
			"doctype": "App Release",
			"app": app_source.app,
			"source": app_source.name,
			"hash": hash,
			"message": "Test Msg",
			"author": "Test Author",
			"deployable": True,
			"status": "Approved",
			"team": app_source.team,
		}
	).insert(ignore_if_duplicate=True)
	app_release.reload()
	return app_release


class TestAppRelease(FrappeTestCase):
	def setUp(self):
		from press.press.doctype.app.test_app import create_test_app
		from press.press.doctype.app_source.test_app_source import create_test_app_source
		from press.press.doctype.team.test_team import create_test_team

		self.team = create_test_team()
		self.app = create_test_app("frappe", "Frappe Framework")
		self.app_source = create_test_app_source("Version 14", self.app, team=self.team.name)

	def tearDown(self):
		frappe.db.rollback()

	# -----------------------------------------------------------------------
	# before_save auto-approval
	# -----------------------------------------------------------------------

	def _make_release(self, status="Awaiting Approval", public=True) -> AppRelease:
		"""Build an unsaved AppRelease doc for testing before_save hooks."""
		release = frappe.new_doc("App Release")
		release.app = self.app.name
		release.source = self.app_source.name
		release.hash = frappe.mock("sha1")
		release.team = self.team.name
		release.status = status
		release.public = public
		return release

	def test_before_save_auto_approves_featured_app(self):
		"""App releases for Featured Apps in Marketplace Settings are auto-approved."""
		release = self._make_release(status="Awaiting Approval")
		with patch("frappe.get_all") as mock_get_all:
			# Featured apps contains our app name, no auto-release teams
			def _get_all(doctype, *args, **kwargs):
				if "Featured App" in doctype or (
					kwargs.get("filters", {}) == {"parent": "Marketplace Settings"}
					and doctype == "Featured App"
				):
					return [self.app.name]
				if "Auto Release Team" in doctype or doctype == "Auto Release Team":
					return []
				return frappe.db.get_all(doctype, *args, **kwargs)

			mock_get_all.side_effect = _get_all
			release.before_save()
		self.assertEqual(release.status, "Approved")

	def test_before_save_auto_approves_auto_release_team(self):
		"""Auto Release Teams get their releases auto-approved."""
		release = self._make_release(status="Awaiting Approval")
		with patch("frappe.get_all") as mock_get_all:

			def _get_all(doctype, *args, **kwargs):
				if doctype == "Featured App":
					return []
				if doctype == "Auto Release Team":
					return [self.team.name]
				return frappe.db.get_all(doctype, *args, **kwargs)

			mock_get_all.side_effect = _get_all
			release.before_save()
		self.assertEqual(release.status, "Approved")

	def test_before_save_does_not_change_status_for_regular_release(self):
		"""Regular (non-featured, non-auto-team) releases keep their status."""
		release = self._make_release(status="Awaiting Approval")
		with patch("frappe.get_all") as mock_get_all:
			# Neither featured app nor auto-release team
			mock_get_all.side_effect = lambda *a, **kw: []
			release.before_save()
		self.assertEqual(release.status, "Awaiting Approval")

	# -----------------------------------------------------------------------
	# _has_auto_deploy_marker
	# -----------------------------------------------------------------------

	def test_has_auto_deploy_marker_returns_false_when_no_marker_configured(self):
		release = self._make_release()
		release.message = "[fc-deploy] some message"
		with patch("frappe.db.get_single_value", return_value=None):
			has_marker, bench_group = release._has_auto_deploy_marker()
		self.assertFalse(has_marker)
		self.assertIsNone(bench_group)

	def test_has_auto_deploy_marker_returns_false_when_marker_not_in_message(self):
		release = self._make_release()
		release.message = "Regular commit message"
		with patch("frappe.db.get_single_value", return_value="[fc-deploy]"):
			has_marker, _bench_group = release._has_auto_deploy_marker()
		self.assertFalse(has_marker)

	def test_has_auto_deploy_marker_returns_true_when_marker_present(self):
		release = self._make_release()
		release.message = "Fix bug [fc-deploy]"
		with patch("frappe.db.get_single_value", return_value="[fc-deploy]"):
			has_marker, _bench_group = release._has_auto_deploy_marker()
		self.assertTrue(has_marker)

	def test_has_auto_deploy_marker_extracts_bench_group_from_message(self):
		release = self._make_release()
		release.message = "Deploy fix [fc-deploy]-my-bench-group"
		with patch("frappe.db.get_single_value", return_value="[fc-deploy]"):
			has_marker, bench_group = release._has_auto_deploy_marker()
		self.assertTrue(has_marker)
		self.assertEqual(bench_group, "my-bench-group")

	# -----------------------------------------------------------------------
	# has_permission helper
	# -----------------------------------------------------------------------

	def test_has_permission_allows_own_team_to_access_release(self):
		from press.press.doctype.app_release.app_release import has_permission

		release = create_test_app_release(self.app_source)
		release.team = self.team.name
		release.public = False

		with (
			patch("frappe.db.get_value", return_value="Website User"),
			patch("press.utils.get_current_team", return_value=self.team.name),
		):
			result = has_permission(release, "read", self.team.user)
		self.assertTrue(result)

	def test_has_permission_blocks_other_team_from_private_release(self):
		from press.press.doctype.app_release.app_release import has_permission
		from press.press.doctype.team.test_team import create_test_team

		other_team = create_test_team()
		release = create_test_app_release(self.app_source)
		release.team = self.team.name
		release.public = False

		with (
			patch("frappe.db.get_value", return_value="Website User"),
			patch("press.utils.get_current_team", return_value=other_team.name),
		):
			result = has_permission(release, "read", other_team.user)
		self.assertFalse(result)

	def test_has_permission_allows_any_team_to_access_public_release(self):
		from press.press.doctype.app_release.app_release import has_permission
		from press.press.doctype.team.test_team import create_test_team

		other_team = create_test_team()
		release = create_test_app_release(self.app_source)
		release.team = self.team.name
		release.public = True  # Public release

		with (
			patch("frappe.db.get_value", return_value="Website User"),
			patch("press.utils.get_current_team", return_value=other_team.name),
		):
			result = has_permission(release, "read", other_team.user)
		self.assertTrue(result)

	def test_has_permission_allows_system_user(self):
		from press.press.doctype.app_release.app_release import has_permission

		release = create_test_app_release(self.app_source)
		release.team = self.team.name
		release.public = False

		# System users always have permission
		with patch("frappe.db.get_value", return_value="System User"):
			result = has_permission(release, "read", "Administrator")
		self.assertTrue(result)

	# -----------------------------------------------------------------------
	# set_invalid
	# -----------------------------------------------------------------------

	def test_set_invalid_marks_release_and_records_reason(self):
		release = self._make_release()
		self.assertFalse(release.invalid_release)
		release.set_invalid("Syntax error in hooks.py")
		self.assertTrue(release.invalid_release)
		self.assertEqual(release.invalidation_reason, "Syntax error in hooks.py")
