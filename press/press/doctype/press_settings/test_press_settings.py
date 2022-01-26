# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest

from press.press.doctype.cluster.test_cluster import create_test_cluster


def create_test_press_settings():
	"""Create test press settings doc"""
	create_test_cluster()
	if not frappe.db.exists("TLS Certificate", "*.fc.dev"):
		frappe.get_doc(
			{
				"doctype": "TLS Certificate",
				"name": "*.fc.dev",
				"domain": "fc.dev",
				"wildcard": True,
				"status": "Active",
				"rsa_key_size": 2048,
			}
		).db_insert()

	frappe.get_doc(
		{
			"doctype": "Root Domain",
			"name": "fc.dev",
			"dns_provider": "AWS Route 53",
			"default_cluster": "Default",
			"aws_access_key_id": frappe.mock("password"),
			"aws_secret_access_key": frappe.mock("password"),
		}
	).insert(ignore_if_duplicate=True)

	settings = frappe.get_doc(
		{
			"doctype": "Press Settings",
			"domain": "fc.dev",
			"bench_configuration": "{}",
			"rsa_key_size": "2048",
			"certbot_directory": ".certbot",
			"eff_registration_email": frappe.mock("email"),
		}
	).insert()
	return settings


class TestPressSettings(unittest.TestCase):
	pass
