# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.tests.dashboard_request import DashboardRequestTestCase


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestSiteActionRequests(DashboardRequestTestCase):
	def setUp(self):
		super().setUp()
		self.app = create_test_app()
		self.other_app = create_test_app("erpnext", "ERPNext")
		group = create_test_release_group([self.app, self.other_app], user=self.email)
		bench = create_test_bench(group=group)
		self.site = create_test_site(bench=bench.name, team=self.team.name, apps=[self.app.name])
		frappe.db.commit()

	def job_types(self) -> list[str]:
		return frappe.get_all("Agent Job", {"site": self.site.name}, pluck="job_type")

	def test_install_app_creates_the_install_job_and_user_is_still_logged_in(self):
		self.login()

		self.assertSucceeded(self.run_doc_method(self.site, "install_app", {"app": self.other_app.name}))

		self.assertIn("Install App on Site", self.job_types())
		self.assertStillLoggedIn()

	def test_uninstall_app_creates_the_uninstall_job_and_user_is_still_logged_in(self):
		self.login()

		uninstall = self.run_doc_method(
			self.site, "uninstall_app", {"app": self.app.name, "create_offsite_backup": False, "feedback": ""}
		)

		self.assertSucceeded(uninstall)
		self.assertIn("Uninstall App from Site", self.job_types())
		self.assertStillLoggedIn()

	def test_archive_creates_the_archive_job_and_user_is_still_logged_in(self):
		self.login()

		archive = self.run_doc_method(self.site, "archive", {"force": False, "create_offsite_backup": False})

		self.assertSucceeded(archive)
		self.assertIn("Archive Site", self.job_types())
		self.assertStillLoggedIn()

	@patch("frappe.enqueue_doc")
	def test_fetch_certificate_queues_the_certificate_and_user_is_still_logged_in(self, enqueue_doc):
		certificate = frappe.get_doc(
			{
				"doctype": "TLS Certificate",
				"name": f"{frappe.generate_hash(8)}.test",
				"status": "Failure",
				"provider": "Let's Encrypt",
				"rsa_key_size": "2048",
				"retry_count": 0,
			}
		)
		certificate.domain = certificate.name
		certificate.db_insert()
		frappe.db.commit()
		self.login()

		self.assertSucceeded(
			self.run_doc_method(self.site, "fetch_certificate", {"domain": certificate.domain})
		)

		enqueue_doc.assert_called_once()
		self.assertStillLoggedIn()
