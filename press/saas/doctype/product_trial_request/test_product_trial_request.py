# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.saas.doctype.ai_settings.test_ai_settings import enrolled


@patch.object(Site, "create_sync_user_webhook", new=Mock())
@patch("frappe.enqueue_doc", new=Mock())
class TestProductTrialRequest(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_site_created_asks_for_a_grove_key_only_while_press_is_enrolled(self):
		site = create_test_site()
		for enrolment, expected in ((dict(control_api_key="", control_api_secret=""), None), ({}, "Pending")):
			enrolled(**enrolment)
			request = frappe.get_doc(
				{"doctype": "Product Trial Request", "site": site.name, "status": "Wait for Site"}
			).insert()
			request.status = "Site Created"
			request.save()
			self.assertEqual(
				frappe.db.get_value("Grove Key Request", {"product_trial_request": request.name}, "status"),
				expected,
			)
