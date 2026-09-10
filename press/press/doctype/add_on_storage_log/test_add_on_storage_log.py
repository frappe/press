# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.server.test_server import create_test_server


def create_test_add_on_storage_log(current_disk_usage: float, available_disk_space: float):
	return frappe.get_doc(
		{
			"doctype": "Add On Storage Log",
			"server": create_test_server().name,
			"mountpoint": "/opt/volumes/benches",
			"current_disk_usage": current_disk_usage,
			"available_disk_space": available_disk_space,
			"adding_storage": 50,
			"is_warning": True,
		}
	).insert()


class IntegrationTestAddOnStorageLog(FrappeTestCase):
	"""
	Integration tests for AddOnStorageLog.
	Use this class for testing interactions between multiple components.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def test_used_storage_percentage_is_rounded_share_of_capacity(self):
		log = create_test_add_on_storage_log(current_disk_usage=85.4, available_disk_space=100)

		self.assertEqual(log.used_storage_percentage, 85)

	def test_used_storage_percentage_is_zero_without_a_known_capacity(self):
		log = create_test_add_on_storage_log(current_disk_usage=85.4, available_disk_space=0)

		self.assertEqual(log.used_storage_percentage, 0)
