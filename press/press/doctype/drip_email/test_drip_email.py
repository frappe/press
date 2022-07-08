# -*- coding: utf-8 -*-
# Copyright (c) 2015, Web Notes and Contributors
# See license.txt


import frappe
import unittest


from typing import Optional
from datetime import date, timedelta
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.account_request.test_account_request import (
	create_test_account_request,
)
from press.saas.doctype.saas_app.test_saas_app import create_test_saas_app


def create_test_drip_email(send_after: int, saas_app: Optional[str] = None):
	return frappe.get_doc(
		{
			"doctype": "Drip Email",
			"sender": "test@test.com",
			"sender_name": "Test User",
			"subject": "Drip Test",
			"message": "Drip Top, Drop Top",
			"send_after": send_after,
			"saas_app": saas_app,
		}
	).insert(ignore_if_duplicate=True)


class TestDripEmail(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_correct_sites_are_selected_for_drip_email(self):
		test_app = create_test_app()
		test_saas_app = create_test_saas_app(test_app.name)

		drip_email = create_test_drip_email(0, saas_app=test_saas_app.name)

		site1 = create_test_site("site1", standby_for=test_saas_app.name)
		site1.account_request = create_test_account_request(
			"site1", saas=True, saas_app=test_saas_app.name
		).name
		site1.save()

		site2 = create_test_site("site2")
		site2.account_request = create_test_account_request("site2").name
		site2.save()

		create_test_site("site3")  # Note: site is not created

		self.assertEqual(drip_email.sites_to_send_drip, [site1.name])

	def test_older_site_isnt_selected(self):
		drip_email = create_test_drip_email(0)
		site = create_test_site("site1")
		site.account_request = create_test_account_request(
			"site1", creation=date.today() - timedelta(1)
		).name
		site.save()
		self.assertNotEqual(drip_email.sites_to_send_drip, [site.name])
