# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import json
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob, poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.deploy_candidate_difference.test_deploy_candidate_difference import (
	create_test_deploy_candidate_differences,
)
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.site_update.site_update import SiteUpdate
from press.press.doctype.subscription.test_subscription import create_test_subscription


@patch.object(SiteUpdate, "start", new=Mock())
def create_test_site_update(site: str, destination_group: str, status: str) -> SiteUpdate:
	return frappe.get_doc(
		dict(doctype="Site Update", site=site, destination_group=destination_group, status=status)
	).insert(ignore_if_duplicate=True)


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
			f".*apps installed on {site.name}: app., app.$",
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
