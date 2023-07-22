# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest


def create_test_frappe_version(
	number: int = 13,
	nvm: str = "0.36.0",
	node: str = "14.19.0",
	python: str = "3.7",
	wkhtmltopdf: str = "0.12.5",
	bench: str = "5.15.2",
):
	"""Create test Frappe Version doc"""

	dependencies = [
		{"dependency": "NVM_VERSION", "version": nvm},
		{"dependency": "NODE_VERSION", "version": node},
		{"dependency": "PYTHON_VERSION", "version": python},
		{"dependency": "WKHTMLTOPDF_VERSION", "version": wkhtmltopdf},
		{"dependency": "BENCH_VERSION", "version": bench},
	]
	frappe_version = frappe.get_doc(
		{
			"doctype": "Frappe Version",
			"name": f"Version {number}",
			"number": number,
			"status": "Stable",
			"dependencies": dependencies,
		}
	).insert(ignore_if_duplicate=True)
	frappe_version.reload()
	return frappe_version


class TestFrappeVersion(unittest.TestCase):
	def test_create_frappe_version_with_default_dependencies(self):
		frappe_version = create_test_frappe_version(13)
		self.assertEqual(len(frappe_version.dependencies), 5)
