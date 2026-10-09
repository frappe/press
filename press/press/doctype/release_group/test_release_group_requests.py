# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench
from press.tests.dashboard_request import DashboardRequestTestCase


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestReleaseGroupRequests(DashboardRequestTestCase):
	def setUp(self):
		super().setUp()
		self.group = create_test_release_group([create_test_app()], user=self.email)
		self.bench = create_test_bench(group=self.group)
		# the bench is up, so the job that created it is done
		frappe.db.set_value("Agent Job", {"bench": self.bench.name}, "status", "Success")
		frappe.db.commit()

	def test_drop_bench_group_archives_its_benches_and_user_is_still_logged_in(self):
		self.login()

		# the Drop Bench action deletes the group through the document resource
		drop = self.post("press.api.client.delete", {"doctype": "Release Group", "name": self.group.name})

		self.assertSucceeded(drop)
		self.assertEqual(frappe.db.get_value("Release Group", self.group.name, "enabled"), 0)
		self.assertTrue(
			frappe.db.exists("Agent Job", {"bench": self.bench.name, "job_type": "Archive Bench"})
		)
		self.assertStillLoggedIn()
