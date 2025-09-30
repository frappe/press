# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.marketplace_app.utils import (
	get_rating_percentage_distribution,
	number_k_format,
)


def create_test_marketplace_app(app: str, team: str | None = None, sources: list[dict] | None = None):
	marketplace_app = frappe.get_doc(
		{
			"doctype": "Marketplace App",
			"app": app,
			"description": "Test App",
			"team": team,
			"sources": sources,
		}
	).insert(ignore_if_duplicate=True)
	marketplace_app.reload()
	return marketplace_app


class TestMarketplaceApp(FrappeTestCase):
	def test_number_format_util(self):
		test_cases_map = {
			0: "0",
			10: "10",
			999: "999",
			1000: "1k",
			8100: "8.1k",
			8900: "8.9k",
			8990: "9k",
			7102: "7.1k",
			10031: "10k",
			708609: "708.6k",
		}

		for input_value, expected_output in test_cases_map.items():
			self.assertEqual(number_k_format(input_value), expected_output)

	def test_rating_percentage_distribution(self):
		test_table = [
			{
				"test_reviews": [{"rating": 4}, {"rating": 5}, {"rating": 1}],
				"expected_result": {1: 33, 2: 0, 3: 0, 4: 33, 5: 33},
			},
			{
				"test_reviews": [{"rating": 5}, {"rating": 5}, {"rating": 5}],
				"expected_result": {1: 0, 2: 0, 3: 0, 4: 0, 5: 100},
			},
			{
				"test_reviews": [],
				"expected_result": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
			},
		]

		for test_case in test_table:
			test_reviews = test_case["test_reviews"]
			test_reviews = [frappe._dict(r) for r in test_reviews]
			got = get_rating_percentage_distribution(test_reviews)

			self.assertDictEqual(got, test_case["expected_result"])
