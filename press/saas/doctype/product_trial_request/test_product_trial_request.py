# Copyright (c) 2023, Frappe and Contributors
# See license.txt
"""A visitor signs up for a product trial and gets a site."""

from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.root_domain.root_domain import get_domains
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_bench
from press.press.doctype.team.test_team import create_test_team
from press.saas.doctype.product_trial.product_trial import ProductTrial
from press.saas.doctype.product_trial.test_product_trial import create_test_product_trial
from press.saas.doctype.product_trial_request.product_trial_request import (
	ProductTrialRequest,
	expire_long_pending_trial_requests,
)


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
# Site Created connects to the new site over HTTPS, which the test site cannot reach
@patch.object(Site, "create_sync_user_webhook", new=Mock())
class TestProductTrialRequest(FrappeTestCase):
	def setUp(self):
		self.product = create_test_product_trial(create_test_app("test_trial_request", "Test Trial Request"))
		self.bench = create_test_bench(group=frappe.get_doc("Release Group", self.product.release_group))
		self.team = create_test_team()
		self.request = self.create_request()
		get_domains.clear_cache()

	def tearDown(self):
		frappe.db.rollback()
		get_domains.clear_cache()

	def create_request(self) -> ProductTrialRequest:
		return frappe.get_doc(
			doctype="Product Trial Request", product_trial=self.product.name, team=self.team.name
		).insert()

	def create_site(self, subdomain: str = "trial-customer"):
		def on_test_bench(site: Site):
			site.bench, site.server = self.bench.name, self.bench.server

		# The bench pick wants a cluster with proxy servers; the test has one bench
		with patch.object(Site, "set_latest_bench", new=on_test_bench):
			self.request.create_site(subdomain, self.product.domain)

	def finish_create_site_job(self, status: str):
		frappe.db.set_value("Agent Job", self.request.agent_job, "status", status)
		self.request.update_status_from_agent_jobs()

	def test_create_site_without_a_standby_site_starts_a_new_site_for_the_team(self):
		self.create_site()

		self.assertEqual(self.request.status, "Wait for Site")
		self.assertEqual(self.request.site, f"trial-customer.{self.product.domain}")
		self.assertEqual(frappe.db.get_value("Site", self.request.site, "team"), self.team.name)
		self.assertEqual(frappe.db.get_value("Agent Job", self.request.agent_job, "job_type"), "New Site")

	def test_create_site_gives_the_team_owner_a_login_on_the_new_site(self):
		self.create_site()

		self.assertTrue(
			frappe.db.exists("Site User", {"site": self.request.site, "user": self.team.user, "enabled": 1})
		)

	def test_request_is_marked_site_created_when_the_create_site_job_succeeds(self):
		self.create_site()

		self.finish_create_site_job("Success")

		self.assertEqual(self.request.status, "Site Created")
		self.assertTrue(self.request.site_creation_completed_on)

	def test_request_is_marked_as_error_when_the_create_site_job_fails(self):
		self.create_site()

		self.finish_create_site_job("Failure")

		self.assertEqual(self.request.status, "Error")

	def test_request_is_marked_as_error_when_site_setup_fails_unexpectedly(self):
		# log_error re-raises inside tests, which would hide the status change
		with (
			patch.object(ProductTrial, "setup_trial_site", side_effect=Exception("No bench available")),
			patch("press.saas.doctype.product_trial_request.product_trial_request.log_error") as log_error,
		):
			self.create_site()

		self.assertEqual((self.request.status, self.request.error), ("Error", "No bench available"))
		log_error.assert_called_once()

	def test_create_site_with_an_unknown_domain_is_refused_and_leaves_the_request_pending(self):
		with self.assertRaisesRegex(frappe.ValidationError, "The domain is invalid"):
			self.request.create_site("trial-customer", "not-a-root-domain.example.com")

		self.assertEqual(self.request.reload().status, "Pending")

	def test_create_site_a_second_time_does_not_start_another_site(self):
		self.create_site()

		self.create_site("another-subdomain")

		self.assertEqual(self.request.site, f"trial-customer.{self.product.domain}")
		self.assertFalse(Site.exists("another-subdomain", self.product.domain))

	def test_request_left_pending_for_more_than_six_hours_expires(self):
		frappe.db.set_value(
			"Product Trial Request",
			self.request.name,
			"creation",
			add_to_date(now_datetime(), hours=-7),
			update_modified=False,
		)

		expire_long_pending_trial_requests()

		self.assertEqual(self.request.reload().status, "Expired")

	def test_request_pending_for_less_than_six_hours_does_not_expire(self):
		expire_long_pending_trial_requests()

		self.assertEqual(self.request.reload().status, "Pending")
