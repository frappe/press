# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.saas.doctype.grove_settings.test_grove_settings import enrolled
from press.saas.doctype.grove_trial_key.test_grove_trial_key import ai_keys_of, available


@patch.object(Site, "create_sync_user_webhook", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("frappe.enqueue_doc", new=Mock())
class TestProductTrialRequest(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def site_created(self, site: str):
		request = frappe.get_doc(
			{"doctype": "Product Trial Request", "site": site, "status": "Wait for Site"}
		).insert()
		request.status = "Site Created"
		request.save()
		return request

	def test_a_site_created_takes_a_pool_key_only_while_enrolled_and_the_pool_is_on(self):
		site = create_test_site()
		frappe.db.delete("Grove Trial Key")
		key = available()
		cases = (
			(dict(control_api_key="", control_api_secret=""), "Available"),
			(dict(trial_pool_size=0), "Available"),
			({}, "Assigned"),
		)
		for enrolment, expected in cases:
			enrolled(**enrolment)
			request = self.site_created(site.name)
			self.assertEqual(key.reload().status, expected)
		self.assertEqual((key.site, key.product_trial_request), (site.name, request.name))
		self.assertEqual(ai_keys_of(site.name)[0]["api_key"], f"gr_{key.grove_key}")

		request.status, request.error = "Error", "boom"
		request.save()
		request.status = "Site Created"
		request.save()
		self.assertEqual(frappe.db.count("Grove Trial Key", {"site": site.name}), 1)

	def test_an_empty_pool_leaves_the_site_without_ai_and_without_an_error(self):
		enrolled(trial_pool_size=3)
		frappe.db.delete("Grove Trial Key")
		site = create_test_site()

		self.site_created(site.name)

		self.assertIsNone(ai_keys_of(site.name))
