# Copyright (c) 2024, Frappe and Contributors
# See license.txt
"""
Comprehensive test coverage for site.py targeting 90% coverage.

Groups covered:
  Group 1  — Job update processors
  Group 2  — Configuration methods
  Group 3  — Migration & move methods
  Group 4  — Subscription & billing methods
  Group 5  — Database introspection methods
  Group 6  — Scheduler / bulk operations
  Group 7  — Site info / sync methods
  Group 8  — Login / user methods
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.site import (
	ARCHIVE_AFTER_SUSPEND_DAYS,
	CREATION_FAILURE_RETENTION_DAYS,
	Site,
	archive_creation_failed_sites,
	archive_suspended_sites,
	get_new_status_for_archive_attempted_site,
	get_remove_step_status,
	notify_site_scheduled_for_archival,
	process_install_app_site_job_update,
	process_migrate_site_job_update,
	process_move_site_to_bench_job_update,
	process_new_site_job_update,
	process_reinstall_site_job_update,
	process_restore_job_update,
	process_restore_tables_job_update,
	process_uninstall_app_site_job_update,
	send_warning_mail_regarding_sites_exceeding_disk_usage,
	sync_sites_setup_wizard_complete_status,
	update_backup_restoration_test_status,
)
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.team.test_team import create_test_team

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(job_type, status, site_name, request_data=None, output="", upstream=None):
	"""Return a minimal Mock that looks like an AgentJob."""
	job = Mock(spec=AgentJob)
	job.job_type = job_type
	job.status = status
	job.site = site_name
	job.request_data = json.dumps(request_data or {})
	job.output = output
	job.upstream = upstream or ""
	job.name = frappe.generate_hash(length=10)
	job.data = None
	job.retry_count = 0
	return job


def _insert_agent_job(job_type, site_name, server, status="Pending", server_type="Server"):
	"""Insert a real Agent Job doc (needed when frappe.get_last_doc / frappe.get_value is called)."""
	return frappe.get_doc(
		{
			"doctype": "Agent Job",
			"job_type": job_type,
			"site": site_name,
			"server": server,
			"server_type": server_type,
			"status": status,
			"request_method": "POST",
			"request_path": "/test",
			"request_data": "{}",
		}
	).insert(ignore_permissions=True)


def _make_step(agent_job_name, step_name, status):
	"""Insert an Agent Job Step record and return its name."""
	return (
		frappe.get_doc(
			{
				"doctype": "Agent Job Step",
				"agent_job": agent_job_name,
				"step_name": step_name,
				"status": status,
				"duration": "00:00:01",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


# ===========================================================================
# Group 1 — Job update processors
# ===========================================================================


class TestProcessNewSiteJobUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _run(self, job_type, first_status, second_status):
		"""Helper: create a site, fake both agent jobs, call processor."""
		site = create_test_site()
		# First job (mock, not in DB)
		job = _make_job(job_type, first_status, site.name)
		# Second job in DB so frappe.get_value can find it
		other_types = {
			"Add Site to Upstream": ("New Site", "New Site from Backup"),
			"New Site": ("Add Site to Upstream",),
			"New Site from Backup": ("Add Site to Upstream",),
		}[job_type]

		_insert_agent_job(other_types[0], site.name, site.server, status=second_status)

		with (
			patch("press.press.doctype.site.site.Site.sync_apps", new=Mock()),
			patch("press.press.doctype.site.site.marketplace_app_hook", new=Mock()),
			patch("press.press.doctype.site.site.Agent.create_database_access_credentials", new=Mock()),
			patch(
				"press.press.doctype.site.site.update_product_trial_request_status_based_on_site_status",
				new=Mock(),
			),
			patch("press.press.doctype.site.site.create_site_status_update_webhook_event", new=Mock()),
		):
			process_new_site_job_update(job)

		site.reload()
		return site

	def test_both_success_marks_active(self):
		site = self._run("New Site", "Success", "Success")
		self.assertEqual(site.status, "Active")

	def test_first_failure_marks_broken(self):
		site = self._run("New Site", "Failure", "Success")
		self.assertEqual(site.status, "Broken")

	def test_second_failure_marks_broken(self):
		site = self._run("New Site", "Success", "Failure")
		self.assertEqual(site.status, "Broken")

	def test_running_marks_installing(self):
		site = self._run("New Site", "Running", "Pending")
		self.assertEqual(site.status, "Installing")

	def test_pending_stays_pending(self):
		site = self._run("New Site", "Pending", "Pending")
		self.assertEqual(site.status, "Pending")

	def test_delivery_failure_marks_broken(self):
		site = self._run("New Site", "Delivery Failure", "Success")
		self.assertEqual(site.status, "Broken")


class TestProcessInstallAppSiteJobUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _run(self, status):
		site = create_test_site()
		job = _make_job("Install App on Site", status, site.name)
		with (
			patch("press.press.doctype.site.site.Site.sync_apps", new=Mock()),
			patch("press.press.doctype.site.site.create_site_status_update_webhook_event", new=Mock()),
		):
			process_install_app_site_job_update(job)
		site.reload()
		return site

	def test_success_marks_active(self):
		site = self._run("Success")
		self.assertEqual(site.status, "Active")

	def test_failure_marks_active(self):
		site = self._run("Failure")
		self.assertEqual(site.status, "Active")

	def test_running_marks_installing(self):
		site = self._run("Running")
		self.assertEqual(site.status, "Installing")

	def test_pending_stays_pending(self):
		# Pending job on Active site → status updated to Pending
		site = self._run("Pending")
		self.assertEqual(site.status, "Pending")


class TestProcessUninstallAppSiteJobUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _run(self, status):
		site = create_test_site()
		job = _make_job("Uninstall App from Site", status, site.name)
		with (
			patch(
				"press.press.doctype.site_backup.site_backup._create_site_backup_from_agent_job",
				new=Mock(),
			),
			patch("press.press.doctype.site.site.Site.sync_apps", new=Mock()),
			patch("press.press.doctype.site.site.create_site_status_update_webhook_event", new=Mock()),
		):
			process_uninstall_app_site_job_update(job)
		site.reload()
		return site

	def test_success_marks_active(self):
		self.assertEqual(self._run("Success").status, "Active")

	def test_failure_marks_active(self):
		self.assertEqual(self._run("Failure").status, "Active")

	def test_running_marks_installing(self):
		self.assertEqual(self._run("Running").status, "Installing")


class TestProcessRestoreJobUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _run(self, status, output=""):
		site = create_test_site()
		job = _make_job("Restore Site", status, site.name, output=output)
		with (
			patch("press.press.doctype.site.site.Agent.create_database_access_credentials", new=Mock()),
			patch("press.press.doctype.site.site.process_marketplace_hooks_for_backup_restore", new=Mock()),
			patch("press.press.doctype.site.site.Site.set_apps", new=Mock()),
			patch("press.press.doctype.site.site.create_site_status_update_webhook_event", new=Mock()),
		):
			process_restore_job_update(job)
		site.reload()
		return site

	def test_success_marks_active(self):
		self.assertEqual(self._run("Success", output="frappe 1.0").status, "Active")

	def test_failure_marks_broken(self):
		self.assertEqual(self._run("Failure").status, "Broken")

	def test_delivery_failure_marks_active(self):
		self.assertEqual(self._run("Delivery Failure").status, "Active")

	def test_running_marks_installing(self):
		self.assertEqual(self._run("Running").status, "Installing")


class TestProcessReinstallSiteJobUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _run(self, status):
		site = create_test_site()
		job = _make_job("Reinstall Site", status, site.name)
		with (
			patch("press.press.doctype.site.site.Agent.create_database_access_credentials", new=Mock()),
			patch("press.press.doctype.site.site.create_site_status_update_webhook_event", new=Mock()),
		):
			process_reinstall_site_job_update(job)
		site.reload()
		return site

	def test_success_marks_active(self):
		self.assertEqual(self._run("Success").status, "Active")

	def test_failure_marks_broken(self):
		self.assertEqual(self._run("Failure").status, "Broken")

	def test_running_marks_installing(self):
		self.assertEqual(self._run("Running").status, "Installing")


class TestProcessMigrateSiteJobUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _run(self, status):
		site = create_test_site()
		job = _make_job("Migrate Site", status, site.name)
		with (
			patch("press.press.doctype.site.site.create_site_status_update_webhook_event", new=Mock()),
		):
			process_migrate_site_job_update(job)
		site.reload()
		return site

	def test_success_marks_active(self):
		self.assertEqual(self._run("Success").status, "Active")

	def test_failure_marks_broken(self):
		self.assertEqual(self._run("Failure").status, "Broken")

	def test_running_marks_updating(self):
		self.assertEqual(self._run("Running").status, "Updating")

	def test_delivery_failure_marks_active(self):
		self.assertEqual(self._run("Delivery Failure").status, "Active")


class TestProcessRestoreTablesJobUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _run(self, status):
		site = create_test_site()
		job = _make_job("Restore Missing Tables", status, site.name)
		with (
			patch("press.press.doctype.site.site.Site.reset_previous_status", new=Mock()),
			patch("press.press.doctype.site.site.create_site_status_update_webhook_event", new=Mock()),
		):
			process_restore_tables_job_update(job)
		site.reload()
		return site

	def test_running_marks_updating(self):
		self.assertEqual(self._run("Running").status, "Updating")

	def test_failure_marks_broken(self):
		self.assertEqual(self._run("Failure").status, "Broken")


class TestProcessMoveSiteToBenchJobUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _run(self, status, move_step_status="Pending"):
		site = create_test_site()
		dest_bench = create_test_bench()
		dest_group = frappe.db.get_value("Bench", dest_bench.name, "group")
		job = _make_job(
			"Move Site to Bench",
			status,
			site.name,
			request_data={"target": dest_bench.name},
		)
		real_job = _insert_agent_job("Move Site to Bench", site.name, site.server, status=status)
		job.name = real_job.name
		_make_step(real_job.name, "Move Site", move_step_status)
		with (
			patch("press.press.doctype.site.site.create_site_status_update_webhook_event", new=Mock()),
			patch("press.press.doctype.site.site.Site.reset_previous_status", new=Mock()),
		):
			process_move_site_to_bench_job_update(job)
		site.reload()
		return site, dest_bench.name, dest_group

	def test_running_marks_updating(self):
		site, _, _ = self._run("Running")
		self.assertEqual(site.status, "Updating")

	def test_failure_marks_broken(self):
		site, _, _ = self._run("Failure")
		self.assertEqual(site.status, "Broken")

	def test_success_with_move_step_updates_bench(self):
		site, dest_bench, dest_group = self._run("Success", move_step_status="Success")
		self.assertEqual(site.bench, dest_bench)
		self.assertEqual(site.group, dest_group)


class TestUpdateBackupRestorationTestStatus(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _make_backup_test(self, site_name, status="Running"):
		name = frappe.generate_hash(length=10)
		frappe.db.sql(
			"""INSERT INTO `tabBackup Restoration Test`
			(name, test_site, status, site, creation, modified, modified_by, owner, docstatus)
			VALUES (%s, %s, %s, %s, NOW(), NOW(), 'Administrator', 'Administrator', 0)""",
			(name, site_name, status, site_name),
		)
		return frappe.get_doc("Backup Restoration Test", name)

	def test_active_maps_to_success(self):
		site = create_test_site()
		bt = self._make_backup_test(site.name)
		job = _make_job("New Site", "Success", site.name)
		with patch("press.press.doctype.site.site.frappe.db.commit", new=Mock()):
			update_backup_restoration_test_status(job, "Active")
		self.assertEqual(frappe.db.get_value("Backup Restoration Test", bt.name, "status"), "Success")

	def test_broken_maps_to_failure(self):
		site = create_test_site()
		bt = self._make_backup_test(site.name)
		job = _make_job("New Site", "Failure", site.name)
		with patch("press.press.doctype.site.site.frappe.db.commit", new=Mock()):
			update_backup_restoration_test_status(job, "Broken")
		self.assertEqual(frappe.db.get_value("Backup Restoration Test", bt.name, "status"), "Failure")

	def test_no_running_test_is_noop(self):
		site = create_test_site()
		job = _make_job("New Site", "Success", site.name)
		# Should not raise even with no running Backup Restoration Test docs
		with patch("press.press.doctype.site.site.frappe.db.commit", new=Mock()):
			update_backup_restoration_test_status(job, "Active")


class TestGetRemoveStepStatus(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_archive_site_returns_step_status(self):
		site = create_test_site()
		job_doc = _insert_agent_job("Archive Site", site.name, site.server)
		_make_step(job_doc.name, "Archive Site", "Success")
		mock_job = _make_job("Archive Site", "Success", site.name)
		mock_job.name = job_doc.name
		status = get_remove_step_status(mock_job)
		self.assertEqual(status, "Success")

	def test_remove_upstream_returns_step_status(self):
		site = create_test_site()
		job_doc = _insert_agent_job("Remove Site from Upstream", site.name, site.server)
		_make_step(job_doc.name, "Remove Site File from Upstream Directory", "Failure")
		mock_job = _make_job("Remove Site from Upstream", "Failure", site.name)
		mock_job.name = job_doc.name
		status = get_remove_step_status(mock_job)
		self.assertEqual(status, "Failure")


class TestGetNewStatusForArchiveAttemptedSite(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _make_two_jobs(self, first_step_status, second_step_status):
		site = create_test_site()
		server = site.server

		job1 = _insert_agent_job("Archive Site", site.name, server)
		_make_step(job1.name, "Archive Site", first_step_status)

		job2 = _insert_agent_job("Remove Site from Upstream", site.name, server)
		_make_step(job2.name, "Remove Site File from Upstream Directory", second_step_status)

		mock1 = _make_job("Archive Site", "Success", site.name)
		mock1.name = job1.name
		mock2 = _make_job("Remove Site from Upstream", "Success", site.name)
		mock2.name = job2.name
		return mock1, mock2

	def test_both_success_archived(self):
		j1, j2 = self._make_two_jobs("Success", "Success")
		self.assertEqual(get_new_status_for_archive_attempted_site(j1, j2), "Archived")

	def test_one_failure_broken(self):
		j1, j2 = self._make_two_jobs("Failure", "Success")
		self.assertEqual(get_new_status_for_archive_attempted_site(j1, j2), "Broken")

	def test_both_skipped_archived(self):
		j1, j2 = self._make_two_jobs("Skipped", "Skipped")
		self.assertEqual(get_new_status_for_archive_attempted_site(j1, j2), "Archived")


# ===========================================================================
# Group 2 — Configuration methods
# ===========================================================================


class TestUpdateSiteConfig(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_update_site_config_with_dict_creates_agent_job(self):
		site = create_test_site()
		with patch.object(Agent, "update_site_config", return_value=Mock()) as mock_agent:
			site.update_site_config({"maintenance_mode": 1})
			mock_agent.assert_called_once()

	def test_update_site_config_with_list_calls_set_configuration(self):
		site = create_test_site()
		with patch.object(Agent, "update_site_config", return_value=Mock()):
			site.update_site_config([{"key": "test_key", "value": "test_val", "type": "String"}])
		# Should have the key in configuration
		keys = [row.key for row in site.configuration]
		self.assertIn("test_key", keys)


class TestDeleteConfig(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_delete_config_removes_key(self):
		site = create_test_site()
		site._set_configuration([{"key": "my_key", "value": "my_val", "type": "String"}])
		with patch.object(Agent, "update_site_config", return_value=Mock()):
			site.delete_config("my_key")
		site.reload()
		keys = [row.key for row in site.configuration]
		self.assertNotIn("my_key", keys)

	def test_delete_blacklisted_key_is_noop(self):
		from press.utils import get_client_blacklisted_keys

		site = create_test_site()
		blacklisted = get_client_blacklisted_keys()
		if blacklisted:
			result = site.delete_config(blacklisted[0])
			self.assertIsNone(result)


class TestCheckServerScriptEnabledOnPublicBench(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_raises_on_public_bench_for_server_script_enabled(self):
		from press.press.doctype.app.test_app import create_test_app
		from press.press.doctype.release_group.test_release_group import create_test_release_group

		app = create_test_app()
		group = create_test_release_group([app], public=True)
		bench = create_test_bench(group=group)
		site = create_test_site(bench=bench.name)

		# Patch is_group_public and is_this_version_or_above
		with (
			patch.object(type(site), "is_group_public", new_callable=lambda: property(lambda self: True)),
			patch.object(Site, "is_this_version_or_above", return_value=True),
		):
			self.assertRaises(
				frappe.exceptions.ValidationError,
				site.check_server_script_enabled_on_public_bench,
				"server_script_enabled",
			)

	def test_no_raise_for_non_server_script_key(self):
		site = create_test_site()
		# Should not raise for any other key
		site.check_server_script_enabled_on_public_bench("some_other_key")


class TestGetPlanConfig(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_get_plan_config_returns_dict(self):
		plan = create_test_plan("Site", price_usd=10.0, price_inr=750.0)
		site = create_test_site()
		with patch("press.press.doctype.site.site.get_plan_config", return_value={"cpu_time_per_day": 100}):
			config = site.get_plan_config(plan.name)
		self.assertIsInstance(config, dict)


# ===========================================================================
# Group 4 — Subscription & billing methods
# ===========================================================================


class TestUpdateSubscription(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_archived_site_disables_subscription(self):
		site = create_test_site()
		with (
			patch.object(Site, "disable_subscription") as mock_disable,
			patch.object(Site, "enable_subscription") as mock_enable,
		):
			site.status = "Archived"
			site.update_subscription()
			mock_disable.assert_called_once()
			mock_enable.assert_not_called()

	def test_active_site_enables_subscription(self):
		site = create_test_site()
		with (
			patch.object(Site, "enable_subscription") as mock_enable,
			patch.object(Site, "disable_subscription") as mock_disable,
		):
			site.status = "Active"
			site.update_subscription()
			mock_enable.assert_called_once()
			mock_disable.assert_not_called()

	def test_suspended_site_disables_subscription(self):
		site = create_test_site()
		with patch.object(Site, "disable_subscription") as mock_disable:
			site.status = "Suspended"
			site.update_subscription()
			mock_disable.assert_called_once()


class TestCreateSubscription(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_subscription_creates_plan_change(self):
		plan = create_test_plan("Site", price_usd=10.0, price_inr=750.0)
		site = create_test_site()
		with patch.object(Site, "_create_initial_site_plan_change") as mock_create:
			site.create_subscription(plan.name)
			mock_create.assert_called_once_with(plan.name)


class TestGetPlanName(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_returns_plan_attribute(self):
		plan = create_test_plan("Site", price_usd=10.0, price_inr=750.0)
		site = create_test_site()
		site.plan = plan.name
		self.assertEqual(site.get_plan_name(), plan.name)

	def test_explicit_plan_arg(self):
		plan = create_test_plan("Site", price_usd=20.0, price_inr=1500.0)
		site = create_test_site()
		self.assertEqual(site.get_plan_name(plan.name), plan.name)

	def test_raises_if_plan_not_string(self):
		site = create_test_site()
		self.assertRaises(frappe.ValidationError, site.get_plan_name, 123)


# ===========================================================================
# Group 5 — Database introspection methods
# ===========================================================================


class TestDatabaseIntrospectionMethods(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def setUp(self):
		self.site = create_test_site()

	def test_fetch_database_processes_calls_agent(self):
		mock_result = [{"id": 1, "info": "SELECT 1"}]
		with (
			patch.object(Agent, "should_skip_requests", return_value=False),
			patch.object(Agent, "fetch_database_processes", return_value=mock_result),
		):
			result = self.site.fetch_database_processes()
		self.assertEqual(result, mock_result)

	def test_fetch_database_processes_returns_none_when_skip(self):
		with patch.object(Agent, "should_skip_requests", return_value=True):
			result = self.site.fetch_database_processes()
		self.assertIsNone(result)

	def test_is_binlog_indexer_running_returns_bool(self):
		with patch.object(frappe.db, "get_value", return_value=1):
			# Patch at doctype level only for database server
			result = self.site.is_binlog_indexer_running()
		self.assertIsInstance(result, bool)

	def test_get_communication_infos_returns_list(self):
		result = self.site.get_communication_infos()
		self.assertIsInstance(result, list)

	def test_binlog_indexing_service_status_returns_dict(self):
		with (
			patch.object(Site, "is_binlog_indexing_enabled", return_value=False),
			patch.object(Site, "is_binlog_indexer_running", return_value=False),
			patch.object(frappe.db, "get_value", return_value=False),
		):
			result = self.site.binlog_indexing_service_status()
		self.assertIn("enabled", result)
		self.assertIn("indexer_running", result)

	def test_fetch_database_locks_returns_list(self):
		with (
			patch.object(Agent, "fetch_database_locks", return_value=[]),
			patch.object(Site, "sync_info", new=Mock()),
		):
			result = self.site.fetch_database_locks()
		self.assertIsInstance(result, list)

	def test_run_sql_query_empty_query_returns_error(self):
		result = self.site.run_sql_query_in_database("", False)
		self.assertFalse(result["success"])

	def test_run_sql_query_calls_agent(self):
		mock_response = {"success": True, "output": "1"}
		with patch.object(Agent, "run_sql_query_in_database", return_value=mock_response):
			result = self.site.run_sql_query_in_database("SELECT 1", False)
		self.assertTrue(result["success"])

	def test_suggest_database_indexes_no_slow_queries(self):
		with patch(
			"press.press.report.mariadb_slow_queries.mariadb_slow_queries.get_data",
			return_value=[],
		):
			result = self.site.suggest_database_indexes()
		self.assertFalse(result["loading"])
		self.assertEqual(result["data"], [])

	def test_add_database_index_returns_success(self):
		with patch.object(Agent, "add_database_index", return_value=Mock(name="job-123")):
			result = self.site.add_database_index("tabToDo", "status")
		self.assertTrue(result["success"])


# ===========================================================================
# Group 6 — Scheduler / bulk operations
# ===========================================================================


class TestSchedulerBulkOps(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch("press.press.doctype.site.site.frappe.db.commit", new=Mock())
	@patch("press.press.doctype.site.site.frappe.db.rollback", new=Mock())
	@patch("frappe.sendmail", new=Mock())
	def test_archive_suspended_sites_archives_old_site(self):
		site = create_test_site()
		site.db_set("status", "Suspended")
		site.db_set(
			"suspended_at",
			frappe.utils.add_days(frappe.utils.now_datetime(), -(ARCHIVE_AFTER_SUSPEND_DAYS + 1)),
		)
		with (
			patch.object(Site, "archive", new=Mock()) as mock_archive,
			patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as _,
		):
			archive_suspended_sites()
			# Mock archive was called at least once
			mock_archive.assert_called()

	@patch("frappe.sendmail", new=Mock())
	@patch("press.press.doctype.site.site.frappe.db.rollback", new=Mock())
	def test_notify_site_scheduled_for_archival_logs_activity(self):
		site = create_test_site()
		notify_site_scheduled_for_archival(site.name)
		self.assertTrue(
			frappe.db.exists(
				"Site Activity",
				{"site": site.name, "action": "Archive Notification"},
			)
		)

	@patch("frappe.sendmail", new=Mock())
	def test_notify_site_scheduled_for_archival_skips_if_already_notified(self):
		site = create_test_site()
		# Log a recent notification
		from press.press.doctype.site_activity.site_activity import log_site_activity

		log_site_activity(site.name, "Archive Notification")
		# Calling again should not send another mail
		with patch("frappe.sendmail") as mock_mail:
			notify_site_scheduled_for_archival(site.name)
			mock_mail.assert_not_called()

	@patch("frappe.sendmail", new=Mock())
	@patch("press.press.doctype.site.site.frappe.db.commit", new=Mock())
	def test_send_warning_mail_skips_when_enforce_disabled(self):
		frappe.db.set_single_value("Press Settings", "enforce_storage_limits", 0)
		with patch("frappe.sendmail") as mock_mail:
			send_warning_mail_regarding_sites_exceeding_disk_usage()
			mock_mail.assert_not_called()

	@patch("frappe.sendmail", new=Mock())
	@patch("press.press.doctype.site.site.frappe.db.commit", new=Mock())
	def test_send_warning_mail_sends_for_exceeded_sites(self):
		frappe.db.set_single_value("Press Settings", "enforce_storage_limits", 1)
		team = create_test_team()
		site = create_test_site(public_server=True, free=False, team=team.name)
		site.db_set("site_usage_exceeded", 1)
		site.db_set("current_disk_usage", 130)
		site.db_set("current_database_usage", 130)
		site.db_set("site_usage_exceeded_on", frappe.utils.now())
		with patch("frappe.sendmail") as mock_mail:
			send_warning_mail_regarding_sites_exceeding_disk_usage()
			# Mail should be attempted for the exceeded site
			mock_mail.assert_called()

	@patch("press.press.doctype.site.site.frappe.db.commit", new=Mock())
	def test_archive_creation_failed_sites_archives_old_broken_sites(self):
		site = create_test_site()
		site.db_set("status", "Broken")
		site.db_set(
			"creation_failed",
			frappe.utils.add_days(frappe.utils.now_datetime(), -(CREATION_FAILURE_RETENTION_DAYS + 1)),
		)
		with patch.object(Site, "archive", new=Mock()) as mock_archive:
			archive_creation_failed_sites()
			mock_archive.assert_called()

	def test_sync_sites_setup_wizard_enqueues_jobs(self):
		team = create_test_team()
		site = create_test_site(team=team.name)
		site.db_set("status", "Active")
		site.db_set("setup_wizard_complete", 0)
		site.db_set("setup_wizard_status_check_retries", 0)
		site.db_set("setup_wizard_status_check_next_retry_on", frappe.utils.add_days(frappe.utils.now(), -1))
		with patch("press.press.doctype.site.site.frappe.enqueue") as mock_enqueue:
			sync_sites_setup_wizard_complete_status()
			mock_enqueue.assert_called()


# ===========================================================================
# Group 7 — Site info / sync methods
# ===========================================================================


class TestSiteInfoSyncMethods(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def setUp(self):
		self.site = create_test_site()

	def test_sync_info_with_data_inserts_usage(self):
		data = {
			"usage": {
				"backups": 10,
				"database": 20,
				"database_free": 5,
				"public": 15,
				"private": 5,
			},
			"config": {},
			"timezone": "Asia/Kolkata",
		}
		with patch.object(Site, "save", new=Mock()):
			self.site.sync_info(data=data)

		usages = frappe.get_all("Site Usage", {"site": self.site.name}, pluck="name")
		self.assertTrue(len(usages) > 0)

	def test_sync_info_without_data_calls_fetch_info(self):
		with patch.object(Site, "fetch_info", return_value=None) as mock_fetch:
			self.site.sync_info()
			mock_fetch.assert_called_once()

	def test_get_disk_usages_returns_dict(self):
		result = self.site.get_disk_usages()
		self.assertIsInstance(result, dict)

	def test_sync_config_info_detects_change(self):
		self.site.config = "{}"
		changed = self.site._sync_config_info({"new_key": "new_value"})
		self.assertTrue(changed)

	def test_sync_config_info_no_change(self):
		self.site.config = json.dumps({"existing_key": "existing_value"}, indent=4)
		changed = self.site._sync_config_info({})
		self.assertFalse(changed)

	def test_sync_usage_info_inserts_record(self):
		usage = {"backups": 1, "database": 2, "database_free": 0, "public": 3, "private": 4}
		self.site._sync_usage_info(usage)
		usages = frappe.get_all("Site Usage", {"site": self.site.name}, pluck="name")
		self.assertTrue(len(usages) > 0)

	def test_is_responsive_calls_agent(self):
		import requests as req

		mock_resp = Mock()
		mock_resp.status_code = req.codes.ok
		mock_resp.json.return_value = {"message": "pong"}
		with patch("press.press.doctype.site.site.requests.get", return_value=mock_resp):
			result = self.site.is_responsive()
			self.assertTrue(result)

	def test_is_responsive_false_on_exception(self):
		with patch("press.press.doctype.site.site.requests.get", side_effect=Exception("timeout")):
			result = self.site.is_responsive()
			self.assertFalse(result)

	def test_has_paid_returns_bool(self):
		# has_paid returns frappe.db.exists() result — falsy (None/False) when no invoice
		result = self.site.has_paid
		self.assertFalse(result)

	def test_inbound_ip_returns_ip(self):
		result = self.site.inbound_ip
		# Should return a string or None depending on setup
		self.assertTrue(result is None or isinstance(result, str))

	def test_get_current_usage_returns_dict_or_none(self):
		result = self.site.get_current_usage()
		# Either None or a dict
		self.assertTrue(result is None or isinstance(result, dict))

	def test_current_usage_property(self):
		with patch("press.api.analytics.get_current_cpu_usage", return_value=0):
			result = self.site.current_usage
		self.assertTrue(result is None or isinstance(result, dict))

	def test_get_communication_infos_returns_list(self):
		result = self.site.get_communication_infos()
		self.assertIsInstance(result, list)

	def test_update_communication_infos_calls_helper(self):
		with patch(
			"press.press.doctype.communication_info.communication_info.update_communication_infos"
		) as mock_update:
			self.site.update_communication_infos(
				[{"channel": "Email", "type": "Site Activity", "value": "test@test.com"}]
			)
			mock_update.assert_called_once()


# ===========================================================================
# Group 8 — Login / user methods
# ===========================================================================


class TestLoginUserMethods(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def setUp(self):
		self.site = create_test_site()

	def test_get_sid_from_agent_returns_sid(self):
		with patch.object(Agent, "get_site_sid", return_value="abc123"):
			sid = self.site.get_sid_from_agent("Administrator")
			self.assertEqual(sid, "abc123")

	def test_get_sid_from_agent_throws_on_ip_restriction(self):
		import requests as req

		# str(e) must contain "validate_ip_address" for the branch to trigger
		http_err = req.HTTPError("400 Client Error: validate_ip_address for url: ...")
		with patch.object(Agent, "get_site_sid", side_effect=http_err):
			self.assertRaises(frappe.ValidationError, self.site.get_sid_from_agent, "user@test.com")

	def test_get_login_sid_uses_agent_when_direct_login_fails(self):
		with (
			patch(
				"press.press.doctype.site.site.requests.post",
				return_value=Mock(cookies={"sid": "Guest"}),
			),
			patch.object(Site, "get_sid_from_agent", return_value="agent_sid") as mock_agent,
		):
			sid = self.site.get_login_sid("Administrator")
			mock_agent.assert_called_once()
			self.assertEqual(sid, "agent_sid")

	def test_get_login_sid_raises_if_no_sid(self):
		with (
			patch(
				"press.press.doctype.site.site.requests.post",
				return_value=Mock(cookies={}),
			),
			patch.object(Site, "get_sid_from_agent", return_value=None),
		):
			self.assertRaises(frappe.ValidationError, self.site.get_login_sid, "Administrator")

	def test_login_as_admin_returns_url(self):
		with patch.object(Site, "login", return_value="test_sid"):
			url = self.site.login_as_admin()
			self.assertIn("sid=test_sid", url)

	def test_create_user_skips_if_already_created(self):
		self.site.additional_system_user_created = True
		result = self.site.create_user("test@test.com", "Test", "User")
		self.assertIsNone(result)

	def test_create_user_calls_agent(self):
		self.site.additional_system_user_created = False
		with patch.object(Agent, "create_user", return_value=Mock()) as mock_create:
			self.site.create_user("test@test.com", "Test", "User")
			mock_create.assert_called_once()
