# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy_candidate_difference.test_deploy_candidate_difference import (
	create_test_deploy_candidate_differences,
)
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_update.site_update import SiteUpdate
from press.tests.dashboard_request import DashboardRequestTestCase


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestSiteUpdateRequests(DashboardRequestTestCase):
	def setUp(self):
		super().setUp()
		group = create_test_release_group([create_test_app()], user=self.email)
		bench = create_test_bench(group=group)
		newer_bench = create_test_bench(group=group, server=bench.server)
		create_test_deploy_candidate_differences(newer_bench.candidate)
		site = create_test_site(bench=bench.name, team=self.team.name)
		tomorrow = frappe.utils.add_days(frappe.utils.now_datetime(), 1)
		self.site_update = SiteUpdate("Site Update", site.schedule_update(scheduled_time=tomorrow))
		frappe.db.commit()

	def test_update_now_starts_the_scheduled_update_and_user_is_still_logged_in(self):
		self.login()

		# the Update Now button in the site's Updates tab
		self.assertSucceeded(self.run_doc_method(self.site_update, "start"))

		self.assertNotEqual(frappe.db.get_value("Site Update", self.site_update.name, "status"), "Scheduled")
		self.assertStillLoggedIn()
