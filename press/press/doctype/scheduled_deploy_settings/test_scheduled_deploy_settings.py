# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from datetime import datetime
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.scheduled_deploy_settings.scheduled_deploy_settings import (
	deploy_release_group,
	deploy_scheduled_release_groups,
)

MODULE = "press.press.doctype.scheduled_deploy_settings.scheduled_deploy_settings"
WEDNESDAY_7PM = datetime(2026, 9, 30, 19, 0)


@patch.object(AppSource, "create_release", create_test_app_release)
@patch(f"{MODULE}.frappe.db.commit", new=Mock())
@patch(f"{MODULE}.frappe.db.rollback", new=Mock())
class TestScheduledDeploySettings(FrappeTestCase):
	def setUp(self):
		super().setUp()
		app = create_test_app()
		self.group_a = create_test_release_group([app]).name
		self.group_b = create_test_release_group([app]).name

	def tearDown(self):
		frappe.db.rollback()

	def _save_settings(self, rows, enabled=True):
		settings = frappe.get_single("Scheduled Deploy Settings")
		settings.enabled = enabled
		settings.set("groups", rows)
		settings.save()
		return settings

	def test_row_is_due_only_on_its_hour_and_ticked_days(self):
		settings = self._save_settings([{"release_group": self.group_a, "hour": 19, "wednesday": 1}])
		row = settings.groups[0]

		self.assertTrue(row.is_due(WEDNESDAY_7PM))
		self.assertFalse(row.is_due(WEDNESDAY_7PM.replace(hour=18)))
		self.assertFalse(row.is_due(datetime(2026, 10, 1, 19, 0)))  # Thursday

	def test_validate_rejects_hour_outside_0_to_23(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Hour must be between 0 and 23"):
			self._save_settings([{"release_group": self.group_a, "hour": 24, "monday": 1}])

	def test_validate_rejects_row_without_any_day(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Select at least one day"):
			self._save_settings([{"release_group": self.group_a, "hour": 16}])

	def test_validate_rejects_release_group_listed_twice(self):
		with self.assertRaisesRegex(frappe.ValidationError, "is listed more than once"):
			self._save_settings(
				[
					{"release_group": self.group_a, "hour": 16, "monday": 1},
					{"release_group": self.group_a, "hour": 19, "friday": 1},
				]
			)

	@patch(f"{MODULE}.deploy_release_group")
	def test_only_due_groups_are_deployed(self, mock_deploy):
		self._save_settings(
			[
				{"release_group": self.group_a, "hour": 19, "wednesday": 1},
				{"release_group": self.group_b, "hour": 16, "wednesday": 1},
			]
		)

		with patch(f"{MODULE}.frappe.utils.now_datetime", return_value=WEDNESDAY_7PM):
			deploy_scheduled_release_groups()

		mock_deploy.assert_called_once_with(self.group_a)

	@patch(f"{MODULE}.deploy_release_group")
	def test_nothing_is_deployed_when_disabled(self, mock_deploy):
		self._save_settings([{"release_group": self.group_a, "hour": 19, "wednesday": 1}], enabled=False)

		with patch(f"{MODULE}.frappe.utils.now_datetime", return_value=WEDNESDAY_7PM):
			deploy_scheduled_release_groups()

		mock_deploy.assert_not_called()

	@patch(f"{MODULE}.log_error")
	@patch(f"{MODULE}.deploy_release_group", side_effect=[Exception("build failed"), None])
	def test_one_failing_group_does_not_block_the_rest(self, mock_deploy, mock_log_error):
		self._save_settings(
			[
				{"release_group": self.group_a, "hour": 19, "wednesday": 1},
				{"release_group": self.group_b, "hour": 19, "wednesday": 1},
			]
		)

		with patch(f"{MODULE}.frappe.utils.now_datetime", return_value=WEDNESDAY_7PM):
			deploy_scheduled_release_groups()

		self.assertEqual(mock_deploy.call_count, 2)
		mock_log_error.assert_called_once()

	@patch(f"{MODULE}.get_bench_update")
	def test_group_without_updates_is_skipped(self, mock_get_bench_update):
		with patch.object(
			ReleaseGroup, "deploy_information", return_value=frappe._dict(update_available=False)
		):
			deploy_release_group(self.group_a)

		mock_get_bench_update.assert_not_called()

	@patch(f"{MODULE}.get_bench_update")
	def test_group_with_updates_is_deployed(self, mock_get_bench_update):
		apps = [{"app": "frappe", "release": "some-release"}]
		with (
			patch.object(
				ReleaseGroup, "deploy_information", return_value=frappe._dict(update_available=True)
			),
			patch.object(ReleaseGroup, "get_apps_to_update", return_value=apps),
		):
			build = deploy_release_group(self.group_a)

		self.assertEqual(build, mock_get_bench_update.return_value.deploy.return_value)
		mock_get_bench_update.assert_called_once_with(self.group_a, apps, ignore_permissions=True)
		mock_get_bench_update.return_value.deploy.assert_called_once_with(
			run_will_fail_check=True, ignore_permissions=True
		)

	@patch(f"{MODULE}.deploy_release_group", return_value="build-1")
	def test_deploy_now_deploys_a_listed_group_and_returns_its_build(self, mock_deploy):
		settings = self._save_settings([{"release_group": self.group_a, "hour": 19, "wednesday": 1}])

		self.assertEqual(settings.deploy_now(self.group_a), "build-1")
		mock_deploy.assert_called_once_with(self.group_a)

	@patch(f"{MODULE}.deploy_release_group")
	def test_deploy_now_refuses_a_group_that_is_not_listed(self, mock_deploy):
		settings = self._save_settings([{"release_group": self.group_a, "hour": 19, "wednesday": 1}])

		with self.assertRaisesRegex(frappe.ValidationError, "is not listed in Scheduled Deploy Settings"):
			settings.deploy_now(self.group_b)
		mock_deploy.assert_not_called()
