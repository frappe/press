# -*- coding: utf-8 -*-
# Copyright (c) 2015, Web Notes and Contributors
# See license.txt


from datetime import date, timedelta
import unittest

import frappe

from press.press.doctype.account_request.test_account_request import (
	create_test_account_request,
)
from press.press.doctype.site.test_site import create_test_site


def create_test_drip_email(send_after: int):
	return frappe.get_doc(
		{
			"doctype": "Drip Email",
			"sender": "test@test.com",
			"sender_name": "Test User",
			"subject": "Drip Test",
			"message": "Drip Top, Drop Top",
			"send_after": send_after,
		}
	).insert(ignore_if_duplicate=True)


class TestDripEmail(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_correct_sites_are_selected_for_drip_email(self):
		drip_email = create_test_drip_email(0)
		site = create_test_site("site1")
		site.account_request = create_test_account_request("site1").name
		site.save()
		site2 = create_test_site("site2")
		site2.account_request = create_test_account_request("site1", erpnext=False).name
		site2.save()
		create_test_site("site3")
		self.assertEqual(drip_email.sites_to_send_drip, [site.name])

	def test_older_site_isnt_selected(self):
		drip_email = create_test_drip_email(0)
		site = create_test_site("site1")
		site.account_request = create_test_account_request(
			"site1", creation=date.today() - timedelta(1)
		).name
		site.save()
		self.assertNotEqual(drip_email.sites_to_send_drip, [site.name])
