# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

# import frappe
import unittest
from press.press.doctype.marketplace_app.utils import number_k_format


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
