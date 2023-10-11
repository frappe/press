# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import json
import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.agent_job.agent_job import AgentJob, poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.deploy.deploy import create_deploy_candidate_differences
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)

from press.press.doctype.site.test_site import create_test_bench, create_test_site

from unittest.mock import patch, Mock

from press.press.doctype.site_update.site_update import SiteUpdate


@patch("press.press.doctype.deploy.deploy.frappe.db.commit", new=Mock())
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

		create_deploy_candidate_differences(bench2)  # for site update to be available

		site = create_test_site(bench=bench1.name)
		site.schedule_update()

		agent_job = frappe.get_last_doc("Agent Job", dict(job_type=("like", "Update Site %")))
		self.assertLess(
			dict(skip_search_index=False).items(), json.loads(agent_job.request_data).items()
		)

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

		create_deploy_candidate_differences(bench2)  # for site update to be available

		site = create_test_site(bench=bench1.name)
		site.schedule_update()

		agent_job = frappe.get_last_doc("Agent Job", dict(job_type=("like", "Update Site %")))
		self.assertLess(
			dict(skip_search_index=True).items(), json.loads(agent_job.request_data).items()
		)

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

		create_deploy_candidate_differences(bench2)  # for site update to be available

		site = create_test_site(bench=bench1.name)

		self.assertRaisesRegex(
			frappe.ValidationError,
			f".*apps installed on {site.name}: app., app.$",
			site.schedule_update,
		)

	@patch.object(SiteUpdate, "reallocate_workers")
	def test_site_update_callback_reallocates_workers_after_disable_maintenance_mode_job(
		self,
		mock_reallocate_workers,
	):
		app1 = create_test_app()  # frappe
		app2 = create_test_app("app2", "App 2")
		app3 = create_test_app("app3", "App 3")

		group = create_test_release_group([app1, app2, app3])
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)

		create_deploy_candidate_differences(bench2)  # for site update to be available

		site = create_test_site(bench=bench1.name)

		with fake_agent_job(
			"Update Site Pull",
			"Success",
			steps=[{"name": "Disable Maintenance Mode", "status": "Success"}],
		):
			site.schedule_update()
			poll_pending_jobs()

		mock_reallocate_workers.assert_called_once()
