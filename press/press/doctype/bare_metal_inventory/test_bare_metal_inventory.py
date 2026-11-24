# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


def create_test_bare_metal_inventory(name: str = "bm-test-1", public_ip_address: str = "203.0.113.10"):
	return frappe.get_doc(
		{
			"doctype": "Bare Metal Inventory",
			"name": name,
			"public_ip_address": public_ip_address,
			"domain": "bm-test-1.example.com",
			"private_ip_address": "10.0.0.10",
			"bmc_ip_address": "10.1.0.10",
			"root_user": "root",
			"root_password": "root-secret",
			"bmc_user": "admin",
			"bmc_password": "bmc-secret",
			"default_user": "frappe",
			"default_password": "default-secret",
		}
	).insert()


class TestBareMetalInventory(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_inventory_is_named_by_user(self):
		inventory = create_test_bare_metal_inventory(name="bm-test-1")
		self.assertEqual(inventory.name, "bm-test-1")
		self.assertEqual(inventory.public_ip_address, "203.0.113.10")
		self.assertEqual(inventory.domain, "bm-test-1.example.com")

	def test_passwords_are_stored_encrypted_and_readable(self):
		inventory = create_test_bare_metal_inventory()
		stored = frappe.db.get_value(
			"Bare Metal Inventory",
			inventory.name,
			["root_password", "bmc_password", "default_password"],
			as_dict=True,
		)
		self.assertNotIn("secret", stored.root_password)
		self.assertNotIn("secret", stored.bmc_password)
		self.assertNotIn("secret", stored.default_password)
		self.assertEqual(inventory.get_password("root_password"), "root-secret")
		self.assertEqual(inventory.get_password("bmc_password"), "bmc-secret")
		self.assertEqual(inventory.get_password("default_password"), "default-secret")
