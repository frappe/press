# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import json
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob, poll_pending_jobs
from press.press.doctype.agent_job.agent_job_notifications import get_details
from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.database_server.database_server import DatabaseServer
from press.press.doctype.deploy_candidate_difference.test_deploy_candidate_difference import (
	create_test_deploy_candidate_differences,
)
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.site.site import (
	DEFAULT_MAX_STATEMENT_TIME,
	STATEMENT_TIME_INCREMENT,
	Site,
)
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.site_update.site_update import (
	LARGE_DATABASE_SIZE,
	SiteUpdate,
	is_site_in_deploy_hours,
	run_scheduled_updates,
	sites_with_available_update,
)
from press.press.doctype.subscription.test_subscription import create_test_subscription


@patch.object(SiteUpdate, "start", new=Mock())
def create_test_site_update(
	site: str, destination_group: str, status: str, ignore_validate: bool = False
) -> SiteUpdate:
	doc = frappe.get_doc(
		dict(doctype="Site Update", site=site, destination_group=destination_group, status=status)
	)
	# Tests that only need a Site Update record in a given status (e.g. a Fatal update to
	# recover from) can skip validation, which otherwise requires a real destination bench.
	doc.flags.ignore_validate = ignore_validate
	return doc.insert(ignore_if_duplicate=True)


class TestSiteUpdate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_update_of_v12_site_skips_search_index(self):
		version = "Version 12"
		app = create_test_app()
		app_source = create_test_app_source(version=version, app=app)
		group = create_test_release_group([app], frappe_version=version)
		bench1 = create_test_bench(group=group)

		create_test_app_release(
			app_source=app_source
		)  # creates pull type release diff only but args are same

		bench2 = create_test_bench(group=group, server=bench1.server)
		self.assertNotEqual(bench1, bench2)

		create_test_deploy_candidate_differences(bench2.candidate)  # for site update to be available

		site = create_test_site(bench=bench1.name)
		site.schedule_update()

		agent_job = frappe.get_last_doc("Agent Job", dict(job_type=("like", "Update Site %")))
		self.assertLess(dict(skip_search_index=False).items(), json.loads(agent_job.request_data).items())

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_update_of_non_v12_site_doesnt_skip_search_index(self):
		version = "Version 13"
		app = create_test_app()
		app_source = create_test_app_source(version=version, app=app)
		group = create_test_release_group([app], frappe_version=version)
		bench1 = create_test_bench(group=group)

		create_test_app_release(
			app_source=app_source
		)  # creates pull type release diff only but args are same

		bench2 = create_test_bench(group=group, server=bench1.server)
		self.assertNotEqual(bench1, bench2)

		create_test_deploy_candidate_differences(bench2.candidate)  # for site update to be available

		site = create_test_site(bench=bench1.name)
		site.schedule_update()

		agent_job = frappe.get_last_doc("Agent Job", dict(job_type=("like", "Update Site %")))
		self.assertLess(dict(skip_search_index=True).items(), json.loads(agent_job.request_data).items())

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_site_update_throws_when_destination_doesnt_have_all_the_apps_in_the_site(
		self,
	):
		app1 = create_test_app()  # frappe
		app2 = create_test_app("app2", "App 2")
		app3 = create_test_app("app3", "App 3")

		group = create_test_release_group([app1, app2, app3])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)

		bench2.apps.pop()
		bench2.apps.pop()
		bench2.save()

		create_test_deploy_candidate_differences(bench2.candidate)  # for site update to be available

		site = create_test_site(bench=bench1.name)

		self.assertRaisesRegex(
			frappe.ValidationError,
			".*apps installed on the site: app., app.*",
			site.schedule_update,
		)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	@patch.object(Site, "sync_apps", new=Mock())
	def test_site_update_callback_reallocates_workers_after_disable_maintenance_mode_job(
		self,
	):
		app1 = create_test_app()  # frappe
		app2 = create_test_app("app2", "App 2")
		app3 = create_test_app("app3", "App 3")

		group = create_test_release_group([app1, app2, app3])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)

		create_test_deploy_candidate_differences(bench2.candidate)  # for site update to be available

		site = create_test_site(bench=bench1.name)
		plan = create_test_plan(site.doctype, cpu_time=8)
		create_test_subscription(site.name, plan.name, site.team)
		site.reload()

		server = frappe.get_doc("Server", bench1.server)
		server.disable_agent_job_auto_retry = True
		server.save()
		server.auto_scale_workers()
		bench1.reload()
		bench2.reload()
		self.assertEqual(site.bench, bench1.name)
		self.assertGreater(bench1.gunicorn_workers, 2)
		self.assertGreater(bench1.background_workers, 1)
		self.assertEqual(bench2.gunicorn_workers, 2)
		self.assertEqual(bench2.background_workers, 1)

		with fake_agent_job(
			"Update Site Pull",
			"Success",
			steps=[{"name": "Disable Maintenance Mode", "status": "Success"}],
		):
			site.schedule_update()
			poll_pending_jobs()

		bench1.reload()
		bench2.reload()
		site.reload()

		self.assertEqual(site.bench, bench2.name)
		self.assertEqual(bench1.gunicorn_workers, 2)
		self.assertEqual(bench1.background_workers, 1)
		self.assertGreater(bench2.gunicorn_workers, 2)
		self.assertGreater(bench2.background_workers, 1)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_failed_recovery_should_set_site_update_status_to_fatal(self):
		app1 = create_test_app()  # frappe
		app2 = create_test_app("app2", "App 2")
		app3 = create_test_app("app3", "App 3")

		group = create_test_release_group([app1, app2, app3])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)

		create_test_deploy_candidate_differences(bench2.candidate)  # for site update to be available

		site = create_test_site(bench=bench1.name)
		plan = create_test_plan(site.doctype, cpu_time=8)
		create_test_subscription(site.name, plan.name, site.team)
		site.reload()

		site_update = None

		with fake_agent_job(
			{
				"Update Site Pull": {"status": "Failure"},
				"Recover Failed Site Update": {"status": "Failure"},
			}
		):
			site_update = site.schedule_update()
			poll_pending_jobs()
			poll_pending_jobs()

		self.assertEqual(
			frappe.get_value("Site Update", site_update, "status"),
			"Fatal",
			"Site Update status should be set to Fatal after failed recovery",
		)
		self.assertEqual(
			frappe.get_value("Site", site.name, "fatal_site_update"),
			site_update,
			"Site's fatal_site_update should be set to the last fatal Site Update",
		)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_dont_allow_site_update_if_last_fatal_update_not_resolved(self):
		app1 = create_test_app()  # frappe
		app2 = create_test_app("app2", "App 2")
		app3 = create_test_app("app3", "App 3")
		app4 = create_test_app("app4", "App 4")

		group = create_test_release_group([app1, app2, app3, app4])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)
		bench3 = create_test_bench(group=group, server=bench1.server)

		create_test_deploy_candidate_differences(bench2.candidate)  # for site update to be available
		create_test_deploy_candidate_differences(bench3.candidate)  # for site update to be available

		site = create_test_site(bench=bench1.name)
		plan = create_test_plan(site.doctype, cpu_time=8)
		create_test_subscription(site.name, plan.name, site.team)
		site.reload()

		fatal_site_update = create_test_site_update(site.name, bench2.group, "Fatal")
		site.fatal_site_update = fatal_site_update.name
		site.save()

		with fake_agent_job(
			{
				"Update Site Pull": {"status": "Failure"},
				"Recover Failed Site Update": {"status": "Failure"},
			}
		):
			self.assertRaisesRegex(
				frappe.ValidationError,
				r".*Site has encountered a fatal error during last update*",
				site.schedule_update,
			)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_after_resolving_fatal_site_update_new_update_can_be_scheduled(self):
		app1 = create_test_app()  # frappe
		app2 = create_test_app("app2", "App 2")
		app3 = create_test_app("app3", "App 3")
		app4 = create_test_app("app4", "App 4")

		group = create_test_release_group([app1, app2, app3, app4])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)
		bench3 = create_test_bench(group=group, server=bench1.server)

		create_test_deploy_candidate_differences(bench2.candidate)  # for site update to be available
		create_test_deploy_candidate_differences(bench3.candidate)  # for site update to be available

		site = create_test_site(bench=bench1.name)
		plan = create_test_plan(site.doctype, cpu_time=8)
		create_test_subscription(site.name, plan.name, site.team)
		site.reload()

		fatal_site_update: SiteUpdate = create_test_site_update(site.name, bench2.group, "Fatal")
		site.fatal_site_update = fatal_site_update.name
		site.save()

		fatal_site_update.set_cause_of_failure_is_resolved()
		site.reload()
		self.assertEqual(
			site.fatal_site_update,
			None,
			"Site's fatal_site_update should be reset after resolving the cause of failure",
		)

		with fake_agent_job(
			"Update Site Pull",
			"Success",
		):
			site_update = site.schedule_update()
			poll_pending_jobs()

			self.assertEqual(
				frappe.get_value("Site Update", site_update, "status"),
				"Success",
				"Site Update should be successful",
			)

	@patch("press.press.doctype.site_update.site_update.frappe.db.commit", new=MagicMock)
	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_run_scheduled_updates_starts_scheduled_update(self):
		"""A scheduled update should start and succeed when all validations pass at run time."""
		app = create_test_app()
		group = create_test_release_group([app])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)
		create_test_deploy_candidate_differences(bench2.candidate)
		site = create_test_site(bench=bench1.name)

		past_time = frappe.utils.add_to_date(None, hours=-1)
		site_update_name = site.schedule_update(scheduled_time=past_time)

		with fake_agent_job("Update Site Pull", "Success"):
			run_scheduled_updates()
			poll_pending_jobs()

		self.assertEqual(
			frappe.get_value("Site Update", site_update_name, "status"),
			"Success",
		)

	@patch("press.press.doctype.site_update.site_update.frappe.db.commit", new=MagicMock)
	def test_run_scheduled_updates_fails_if_destination_bench_missing_app(self):
		"""Validation at scheduled run time should catch apps removed from the destination bench after scheduling."""
		app1 = create_test_app()
		app2 = create_test_app("app2", "App 2")
		group = create_test_release_group([app1, app2])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)
		create_test_deploy_candidate_differences(bench2.candidate)
		site = create_test_site(bench=bench1.name)

		past_time = frappe.utils.add_to_date(None, hours=-1)
		site_update_name = site.schedule_update(scheduled_time=past_time)

		bench2_doc = frappe.get_doc("Bench", bench2.name)
		bench2_doc.apps = [a for a in bench2_doc.apps if a.app != app2.name]
		bench2_doc.save()

		run_scheduled_updates()

		self.assertEqual(frappe.get_value("Site Update", site_update_name, "status"), "Cancelled")
		self.assertTrue(frappe.db.exists("Press Notification", {"type": "Site Update", "team": site.team}))

	def test_standby_site_is_updated_even_outside_deploy_hours(self):
		"""A standby site must bypass the deploy-hours filter; regression for is_standby not being fetched."""
		app = create_test_app()
		group = create_test_release_group([app])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)
		create_test_deploy_candidate_differences(bench2.candidate)
		site = create_test_site(bench=bench1.name)
		frappe.db.set_value("Site", site.name, "is_standby", 1)

		[fetched_site] = [s for s in sites_with_available_update(bench1.server) if s.name == site.name]

		# is_standby must be selected, otherwise the deploy-hours bypass is a silent no-op
		self.assertTrue(fetched_site.is_standby)
		# With no deploy hours configured a non-standby site would be filtered out;
		# the standby site must still pass.
		with patch("press.press.doctype.site_update.site_update.frappe.get_hooks", return_value=[]):
			self.assertTrue(is_site_in_deploy_hours(fetched_site))

	@patch("press.press.doctype.site_update.site_update.frappe.db.commit", new=MagicMock)
	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_run_scheduled_updates_fails_if_past_update_to_same_candidates_failed(self):
		"""Validation at scheduled run time should block if an unresolved failure exists for the same source/destination."""
		app = create_test_app()
		group = create_test_release_group([app])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)
		create_test_deploy_candidate_differences(bench2.candidate)
		site = create_test_site(bench=bench1.name)

		# Trigger an immediate update that fails, leaving an unresolved past failure record
		with fake_agent_job(
			{
				"Update Site Pull": {"status": "Failure"},
				"Recover Failed Site Update": {"status": "Failure"},
			}
		):
			site.schedule_update()
			poll_pending_jobs()
			poll_pending_jobs()

		# Reset site state so a new update can be scheduled
		frappe.db.set_value("Site", site.name, "fatal_site_update", None)
		frappe.db.set_value("Site", site.name, "status", "Active")

		# Schedule the update, bypassing the past failure check — that check is what we're testing at run time
		past_time = frappe.utils.add_to_date(None, hours=-1)
		with patch.object(SiteUpdate, "validate_past_failed_updates"):
			site_update_name = site.schedule_update(scheduled_time=past_time)

		run_scheduled_updates()

		self.assertEqual(frappe.get_value("Site Update", site_update_name, "status"), "Cancelled")
		self.assertTrue(frappe.db.exists("Press Notification", {"type": "Site Update", "team": site.team}))

	def _migrate_site_with_difference(self) -> Site:
		app = create_test_app()
		group = create_test_release_group([app])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)
		create_test_deploy_candidate_differences(bench2.candidate)
		# Mark the site's app as a Migrate in the difference so the update's deploy_type is
		# Migrate and recovery uses "Recover Failed Site Migrate".
		difference = frappe.get_doc(
			"Deploy Candidate Difference",
			{"source": bench1.candidate, "destination": bench2.candidate},
		)
		app_row = find(difference.apps, lambda row: row.app == app.name)
		if app_row:
			app_row.deploy_type = "Migrate"
		else:
			difference.append("apps", {"app": app.name, "deploy_type": "Migrate"})
		difference.flags.ignore_validate = True
		difference.save()
		return create_test_site(bench=bench1.name)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_failed_migrate_recovery_restores_site_tables_and_resolves_fatal_update(self):
		site = self._migrate_site_with_difference()

		with fake_agent_job(
			{
				# Move Site succeeding moves the site to the destination bench, so its
				# recovery is a "Recover Failed Site Migrate".
				"Update Site Migrate": {
					"status": "Failure",
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
				# Recovery moved the site back but its table restore hit a transient DB error,
				# so the fallback runs.
				"Recover Failed Site Migrate": {
					"status": "Failure",
					"data": {"output": "Lost connection to MySQL server during query"},
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
				"Restore Site Tables": {"status": "Success"},
			}
		):
			site_update = site.schedule_update()
			poll_pending_jobs()  # Update fails, migrate recovery created
			poll_pending_jobs()  # Migrate recovery fails, Restore Site Tables triggered

			restore_job = frappe.get_value(
				"Agent Job", {"site": site.name, "job_type": "Restore Site Tables"}, "name"
			)
			self.assertTrue(
				restore_job,
				"A failed migrate recovery should trigger a Restore Site Tables job",
			)

			poll_pending_jobs()  # Restore succeeds, site brought back up

		# The update itself failed for good, so it stays Fatal — but with its cause of
		# failure marked resolved, since the fallback restore brought the site back up.
		self.assertEqual(
			frappe.get_value("Site Update", site_update, "status"),
			"Fatal",
			"Site Update should stay Fatal after the fallback table restore",
		)
		self.assertTrue(
			frappe.get_value("Site Update", site_update, "cause_of_failure_is_resolved"),
			"Site Update's cause of failure should be marked resolved after the fallback restore succeeds",
		)
		self.assertEqual(
			frappe.get_value("Site", site.name, "status"),
			"Active",
			"Site should be Active after the fallback table restore succeeds",
		)
		restore_comments = frappe.db.count(
			"Comment",
			{
				"reference_doctype": "Site Update",
				"reference_name": site_update,
				"content": ("like", "%Restore Site Tables%"),
			},
		)
		self.assertEqual(
			restore_comments,
			1,
			"The fallback table restore job should be referenced in a comment on the Site Update",
		)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_failed_migrate_recovery_then_failed_table_restore_goes_fatal(self):
		site = self._migrate_site_with_difference()

		with fake_agent_job(
			{
				"Update Site Migrate": {
					"status": "Failure",
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
				"Recover Failed Site Migrate": {
					"status": "Failure",
					"data": {"output": "Lost connection to MySQL server during query"},
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
				"Restore Site Tables": {"status": "Failure"},
			}
		):
			site_update = site.schedule_update()
			poll_pending_jobs()  # Update fails, migrate recovery created
			poll_pending_jobs()  # Migrate recovery fails, Restore Site Tables triggered
			poll_pending_jobs()  # Table restore also fails, recovery gives up

		self.assertEqual(
			frappe.get_value("Site Update", site_update, "status"),
			"Fatal",
			"Site Update should be Fatal after the fallback table restore also fails",
		)
		self.assertEqual(
			frappe.get_value("Site", site.name, "fatal_site_update"),
			site_update,
			"Site's fatal_site_update should be set after recovery gives up",
		)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_failed_migrate_recovery_before_move_site_does_not_restore_tables(self):
		# If recovery fails at/before Move Site the site is still on the destination bench,
		# so restoring tables would target the wrong bench — the fallback must not run, even
		# though the error is transient.
		site = self._migrate_site_with_difference()

		with fake_agent_job(
			{
				"Update Site Migrate": {
					"status": "Failure",
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
				"Recover Failed Site Migrate": {
					"status": "Failure",
					"data": {"output": "Lost connection to MySQL server during query"},
					"steps": [{"name": "Move Site", "status": "Failure"}],
				},
			}
		):
			site_update = site.schedule_update()
			poll_pending_jobs()  # Update fails, migrate recovery created
			poll_pending_jobs()  # Migrate recovery fails before moving the site back

		self.assertEqual(
			frappe.get_value("Site Update", site_update, "status"),
			"Fatal",
			"Site Update should be Fatal when recovery fails before Move Site",
		)
		self.assertFalse(
			frappe.db.exists("Agent Job", {"site": site.name, "job_type": "Restore Site Tables"}),
			"Restore Site Tables must not run when recovery failed before Move Site",
		)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_failed_migrate_recovery_with_non_transient_error_does_not_restore_tables(self):
		# Only transient DB errors are safely retryable; a non-transient recovery failure
		# should be left Fatal for manual attention, not auto-restored.
		site = self._migrate_site_with_difference()

		with fake_agent_job(
			{
				"Update Site Migrate": {
					"status": "Failure",
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
				"Recover Failed Site Migrate": {
					"status": "Failure",
					"data": {"output": "Table 'tabFoo' doesn't exist"},
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
			}
		):
			site_update = site.schedule_update()
			poll_pending_jobs()  # Update fails, migrate recovery created
			poll_pending_jobs()  # Migrate recovery fails with a non-transient error

		self.assertEqual(
			frappe.get_value("Site Update", site_update, "status"),
			"Fatal",
			"Site Update should be Fatal after a non-transient recovery failure",
		)
		self.assertFalse(
			frappe.db.exists("Agent Job", {"site": site.name, "job_type": "Restore Site Tables"}),
			"Restore Site Tables must not run for a non-transient recovery failure",
		)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_skipped_backups_update_failure_goes_fatal_without_attempting_recovery(self):
		# With backups skipped there is no backup to roll back to, so a failed update must
		# go straight to Fatal — no recover job and, in particular, no Restore Site Tables
		# fallback (there are no tables to restore).
		site = self._migrate_site_with_difference()

		with fake_agent_job(
			{
				"Update Site Migrate": {
					"status": "Failure",
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
			}
		):
			site_update = site.schedule_update(skip_backups=True)
			poll_pending_jobs()  # Update fails

		self.assertEqual(
			frappe.get_value("Site Update", site_update, "status"),
			"Fatal",
			"A skipped-backups update failure should go straight to Fatal",
		)
		for job_type in ("Recover Failed Site Migrate", "Recover Failed Site Update", "Restore Site Tables"):
			self.assertFalse(
				frappe.db.exists("Agent Job", {"site": site.name, "job_type": job_type}),
				f"A skipped-backups update failure should not trigger a {job_type} job",
			)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_restore_tables_success_activates_site_and_resolves_fatal_update(self):
		app1 = create_test_app()

		group = create_test_release_group([app1])
		bench1 = create_test_bench(group=group)

		site = create_test_site(bench=bench1.name)
		fatal_site_update = create_test_site_update(site.name, bench1.group, "Fatal", ignore_validate=True)

		# Simulate state after failed update + failed recovery
		site.status = "Broken"
		site.status_before_update = "Active"
		site.fatal_site_update = fatal_site_update.name
		site.save()

		with fake_agent_job("Restore Site Tables", "Success"):
			site.restore_tables()
			poll_pending_jobs()

		site.reload()
		self.assertEqual(
			site.status,
			"Active",
			"Site should be Active after successful restore_tables",
		)
		self.assertIsNone(
			site.fatal_site_update,
			"fatal_site_update should be cleared after restore_tables success",
		)
		self.assertEqual(
			frappe.get_value("Site Update", fatal_site_update.name, "status"),
			"Fatal",
			"Site Update should stay Fatal after restore_tables success",
		)
		self.assertTrue(
			frappe.get_value("Site Update", fatal_site_update.name, "cause_of_failure_is_resolved"),
			"Site Update's cause of failure should be marked resolved after restore_tables success",
		)

	def test_database_size_returns_latest_usage_in_mb(self):
		site = create_test_site()
		self.assertEqual(site.database_size, 0)

		frappe.get_doc(doctype="Site Usage", site=site.name, database=1536).insert()  # 1.5 GB in MB

		self.assertEqual(site.database_size, 1536)

	@patch.object(DatabaseServer, "_update_mariadb_system_variables", new=Mock())
	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_increase_max_statement_time_bumps_value_by_an_hour(self):
		group = create_test_release_group([create_test_app()])
		bench = create_test_bench(group=group)
		site = create_test_site(bench=bench.name)

		old_timeout, new_timeout = site.increase_max_statement_time()

		self.assertEqual(old_timeout, DEFAULT_MAX_STATEMENT_TIME)
		self.assertEqual(new_timeout, DEFAULT_MAX_STATEMENT_TIME + STATEMENT_TIME_INCREMENT)

		database_server = frappe.get_doc("Database Server", site.database_server_name)
		row = find(
			database_server.mariadb_system_variables,
			lambda x: x.mariadb_variable == "max_statement_time",
		)
		self.assertIsNotNone(row, "max_statement_time should be set on the database server")
		self.assertEqual(row.value_str, str(new_timeout))

	@patch.object(DatabaseServer, "_update_mariadb_system_variables", new=Mock())
	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_recovery_max_statement_time_bump_is_stashed_and_restored(self):
		group = create_test_release_group([create_test_app()])
		bench = create_test_bench(group=group)
		site = create_test_site(bench=bench.name)
		# A database over the threshold qualifies for the recovery-migrate bump.
		frappe.get_doc(
			{"doctype": "Site Usage", "site": site.name, "database": LARGE_DATABASE_SIZE + 1}
		).insert()
		site_update = create_test_site_update(site.name, bench.group, "Pending", ignore_validate=True)
		site_update.deploy_type = "Migrate"

		site_update.bump_max_statement_time_before_recovery(site)

		self.assertEqual(
			site_update.previous_max_statement_time,
			DEFAULT_MAX_STATEMENT_TIME,
			"The pre-bump max_statement_time should be stashed on the Site Update",
		)
		database_server = frappe.get_doc("Database Server", site.database_server_name)
		self.assertEqual(
			int(float(database_server.get_mariadb_variable_value("max_statement_time"))),
			DEFAULT_MAX_STATEMENT_TIME + STATEMENT_TIME_INCREMENT,
		)

		site_update.reload()
		site_update.restore_max_statement_time()

		database_server.reload()
		self.assertEqual(
			int(float(database_server.get_mariadb_variable_value("max_statement_time"))),
			DEFAULT_MAX_STATEMENT_TIME,
			"max_statement_time should be restored to its pre-bump value once recovery ends",
		)
		self.assertFalse(
			frappe.db.get_value("Site Update", site_update.name, "previous_max_statement_time"),
			"The stashed value should be cleared after restoring",
		)

	@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
	def test_successful_migrate_recovery_does_not_restore_site_tables(self):
		# When the recovery itself succeeds there is nothing left to restore, so the
		# Restore Site Tables fallback must not run.
		site = self._migrate_site_with_difference()

		with fake_agent_job(
			{
				"Update Site Migrate": {
					"status": "Failure",
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
				"Recover Failed Site Migrate": {
					"status": "Success",
					"steps": [{"name": "Move Site", "status": "Success"}],
				},
			}
		):
			site_update = site.schedule_update()
			poll_pending_jobs()  # Update fails, migrate recovery created
			poll_pending_jobs()  # Migrate recovery succeeds

		self.assertEqual(
			frappe.get_value("Site Update", site_update, "status"),
			"Recovered",
			"A successful recovery should leave the Site Update Recovered",
		)
		self.assertFalse(
			frappe.db.exists("Agent Job", {"site": site.name, "job_type": "Restore Site Tables"}),
			"Restore Site Tables must not run when the recovery succeeds",
		)

	def test_skipped_backups_update_failure_notification_directs_user_to_ssh(self):
		group = create_test_release_group([create_test_app()])
		bench = create_test_bench(group=group)
		site = create_test_site(bench=bench.name)
		site_update = create_test_site_update(site.name, bench.group, "Fatal", ignore_validate=True)
		frappe.db.set_value(
			"Site Update",
			site_update.name,
			{"skipped_backups": 1, "update_job": "test-update-job"},
		)

		job = frappe._dict(
			name="test-update-job",
			job_type="Update Site Migrate",
			site=site.name,
			traceback="",
			output="some migration error",
		)

		details = get_details(job, "", "")

		self.assertTrue(
			details["is_actionable"],
			"A skipped-backups update failure should be actionable",
		)
		self.assertEqual(
			details["title"],
			"Site update failed and cannot be recovered automatically",
		)
		self.assertIn("SSH", details["message"])
