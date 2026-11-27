# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.nginx_logs import get, site_query
from press.press.doctype.marketplace_app.test_marketplace_app import create_team_with_press_user
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_domain.test_site_domain import create_test_site_domain


class TestNginxLogs(FrappeTestCase):
	def setUp(self):
		self.site = create_test_site()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_query_matches_only_the_domains_of_the_site_on_its_proxy(self):
		create_test_site_domain(self.site.name, "erp.example.com")
		create_test_site_domain(create_test_site().name, "neighbor.example.com")
		proxy = frappe.db.get_value("Server", self.site.server, "proxy_server")

		query = site_query(self.site.name)["bool"]

		self.assertEqual(query["filter"], [{"term": {"agent.name": proxy}}])
		self.assertEqual(
			query["should"],
			[
				{"term": {"http.request.site": domain}}
				for domain in sorted(["erp.example.com", self.site.name])
			],
		)
		self.assertEqual(query["minimum_should_match"], 1)

	def test_user_of_another_team_cannot_read_the_nginx_logs_of_the_site(self):
		frappe.set_user(create_team_with_press_user().user)
		with self.assertRaisesRegex(frappe.PermissionError, "Not Permitted"):
			get(name=self.site.name, timezone="Asia/Kolkata", date="2026-11-26")
