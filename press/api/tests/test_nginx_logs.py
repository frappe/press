# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.nginx_logs import get, site_query, to_histogram
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
			get(
				name=self.site.name,
				timezone="Asia/Kolkata",
				start="2026-11-26T11:25:00Z",
				end="2026-11-26T11:35:00Z",
			)


class TestNginxLogsHistogram(FrappeTestCase):
	def test_histogram_has_one_stacked_dataset_per_status_class_in_bucket_order(self):
		def bucket(label: str, ok: int, client_errors: int, server_errors: int) -> dict:
			counts = [ok, client_errors, server_errors]
			return {"key_as_string": label, "status": {"buckets": [{"doc_count": c} for c in counts]}}

		histogram = to_histogram([bucket("11:25", 7, 1, 0), bucket("11:30", 2, 0, 5)])

		self.assertEqual(histogram["labels"], ["11:25", "11:30"])
		self.assertEqual(
			[(d["path"], d["stack"], d["values"]) for d in histogram["datasets"]],
			[("2xx, 3xx", "status", [7, 2]), ("4xx", "status", [1, 0]), ("5xx", "status", [0, 5])],
		)
