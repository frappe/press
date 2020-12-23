# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest


def create_test_press_settings():
	"""Create test press settings doc"""
	settings = frappe.get_doc(
		{
			"doctype": "Press Settings",
			"domain": "fc.dev",
			"bench_configuration": "JSON",
			"dns_provider": "AWS Route 53",
			"rsa_key_size": "2048",
		}
	).insert()
	return settings


class TestPressSettings(unittest.TestCase):
	pass
