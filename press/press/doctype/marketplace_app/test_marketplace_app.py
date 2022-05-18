# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import frappe
import unittest

from press.press.doctype.marketplace_app.utils import (
	number_k_format,
	get_rating_percentage_distribution,
)


class TestMarketplaceApp(unittest.TestCase):
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
