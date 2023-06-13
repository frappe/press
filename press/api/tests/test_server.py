# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import frappe

from press.press.doctype.team.test_team import create_test_press_admin_team

from frappe.tests.utils import FrappeTestCase


class TestAPIServer(FrappeTestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()

	def tearDown(self):
		frappe.db.rollback()

	def test_create_new_server_works(self):
		pass
